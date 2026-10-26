"""Replan the unvisited suffix of a tour on mapped pedestrian paths.

Distances are the project's OSM snapshot, not live walking instructions. The
planner locks completed stops and the current stop; optional reordering applies
only to future stops. It never certifies accessibility.
"""
import hashlib
import json
import math
import re

from .route_recommender import _features, get_spot_profile, normalize_preferences


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, default=str).encode()).hexdigest()


def parse_change(text):
    """Conservative bilingual intent parsing; numeric limits are never invented."""
    q = text.lower().strip().replace('个小时', '小时')
    active = bool(re.search(r'只剩|还剩|剩下|提前离园|早点离园|回出口|调整路线|改.*路线|少走|走不动|累了|跳过|不去|不想去|不想爬|避开|minutes? left|hours? left|tired|skip|replan|leave early|less walking|avoid stairs', q))
    if re.search(r'不(?:需要|用|要)调整|不用改|不累|not tired|do not replan', q):
        active = False
    minutes = None
    number = r'(\d+(?:\.\d+)?|半|[一二两三四五六七八九十]+)'
    match = re.search(number + r'\s*(分钟|小时|minutes?|mins?|hours?|hrs?)', q)
    if match:
        raw, unit = match.groups()
        digits = dict(zip('一二两三四五六七八九', [1, 2, 2, 3, 4, 5, 6, 7, 8, 9]))
        if raw == '半': value = .5
        elif '十' in raw:
            a, b = raw.split('十'); value = digits.get(a, 1) * 10 + digits.get(b, 0)
        elif raw in digits: value = digits[raw]
        else: value = float(raw)
        minutes = round(value * (60 if unit.startswith(('h', '小时')) else 1))
    if match and match.group(2).startswith(('h', '小时')) and q[match.end():].lstrip().startswith('半'): minutes += 30
    if re.search(r'半小时|half an? hour', q): minutes = 30
    return {'active': active, 'remaining_minutes': minutes,
            'pace': 'relaxed' if re.search(r'累了|走不动|少走|不想爬|避开.*台阶|tired|less walking|avoid stairs', q) else None,
            'exit_area': next((area for pattern, area in [(r'北宫门|北门|north', 'north'),
                (r'东宫门|东门|east', 'east'), (r'南门|南侧|south', 'south')] if re.search(pattern, q)), None),
            'skip_next': bool(re.search(r'下一站.*(?:不想去|不去|跳过)|跳过下一站|skip (?:the next|next) stop', q)) and not bool(re.search(r'不要跳过|不用跳过|do not skip|don.t skip', q))}


def repair_route(route, index, catalog, minutes, pace='standard', end_area='auto', excluded=None,
                 preferences=None, reserve=0, *, required=None, avoid_steps=None,
                 scenario='time', strategy='highlights', allow_reorder=False, original_plan=None):
    from .walking_network import distance_between, gate_distance, NETWORK, network_version
    from .route_presentation import route_overview
    if not route or not 0 <= index < len(route): raise ValueError('路线进度不可用')
    if len(route) > 20: raise ValueError('路线最多支持20站，请先精简行程')
    if minutes is not None and not 1 <= minutes <= 480: raise ValueError('剩余时间须为1至480分钟')
    if len({s['spot_id'] for s in route}) != len(route): raise ValueError('路线中有重复景点，请重新规划')
    if end_area not in ('auto', *NETWORK['gates']): raise ValueError('离园出口不可用')
    if scenario == 'exit' and end_area == 'auto': raise ValueError('请选择具体离园出口')
    anchor, suffix = route[index], route[index+1:]
    if any(not get_spot_profile(s) for s in [anchor]+suffix):
        raise ValueError('部分景点缺少步行路网接入点，暂不能自动调整')
    excluded, required = set(excluded or []), set(required or [])
    remaining_ids = {s['spot_id'] for s in suffix}
    if not (excluded | required) <= remaining_ids: raise ValueError('只能调整尚未游览的景点')
    if excluded & required: raise ValueError('必游景点不能同时跳过')
    if scenario == 'exit' and required: raise ValueError('直接离园时请先取消必游景点')
    avoid_steps = pace == 'relaxed' if avoid_steps is None else bool(avoid_steps)
    eligible = [s for s in suffix if s['spot_id'] not in excluded and not (avoid_steps and _features(s)['stairs'])]
    if scenario == 'exit': eligible = []
    if required - {s['spot_id'] for s in eligible}: raise ValueError('必游景点与避台阶条件冲突，请调整条件')
    speed = 55 if pace == 'relaxed' else 75
    active_preferences = normalize_preferences(preferences or [])
    def value(s):
        affinity = _features(s)['affinities']
        return sum(affinity.get(p, 0) for p in (list(affinity) if active_preferences == ['comprehensive'] else active_preferences))

    def overview(sequence, avoid):
        return route_overview([anchor]+sequence, pace, include_first_visit=False,
                              end_area=end_area, avoid_steps=avoid, reserve=reserve)
    def public_totals(data):
        return dict(visit_minutes=data['visit_minutes'], walk_minutes=data['walking_minutes'],
                    rest_minutes=data['rest_minutes'], exit_minutes=data['exit_minutes'],
                    reserve_minutes=data['reserve_minutes'], total_minutes=data['total_minutes'], walking_meters=data['walking_meters'])

    baseline = original_plan if isinstance(original_plan, dict) else dict(pace=pace, end_area=end_area)
    original = route_overview([anchor]+suffix, baseline.get('pace', 'standard'), include_first_visit=False,
        end_area=baseline.get('end_area', 'auto'),
        avoid_steps=baseline.get('avoid_steps', baseline.get('pace') == 'relaxed'),
        reserve=baseline.get('reserve_minutes', baseline.get('queue_reserve_minutes', 0)))
    n = len(eligible)
    vertices = eligible+[anchor]
    distances = [[distance_between(a, b, avoid_steps) for b in vertices] for a in vertices]
    exits = [gate_distance(s, end_area, avoid_steps) if end_area != 'auto' else 0 for s in vertices]
    visits = [max(1, int(s.get('visit_duration') or 10)) for s in eligible]
    values = [value(s) for s in eligible]
    required_mask = sum(1 << i for i, s in enumerate(eligible) if s['spot_id'] in required)

    def costs(last, walk, meters, visiting):
        exit_m = exits[last]
        if not math.isfinite(exit_m): return None
        exit_minutes = math.ceil(exit_m/speed)
        rest = math.ceil((walk+visiting+exit_minutes)*(.15 if pace=='relaxed' else .08))
        return dict(visit_minutes=visiting, walk_minutes=walk, rest_minutes=rest,
            exit_minutes=exit_minutes, reserve_minutes=reserve,
            total_minutes=visiting+walk+rest+exit_minutes+reserve, walking_meters=round(meters+exit_m))

    # Subset/end-point dynamic programming. For larger catalogues bound the
    # frontier deterministically; the UI promises a trade-off, not global optimality.
    layer = {(0, n): (0, 0, (), 0, 0)}
    candidates = {}
    capped = n > 12
    for depth in range(n+1):
        next_layer = {}
        for (mask, last), (walk, meters, path, visiting, score) in layer.items():
            totals = costs(last, walk, meters, visiting)
            if mask & required_mask == required_mask and totals and (minutes is None or totals['total_minutes'] <= minutes):
                old = candidates.get(mask)
                if old is None or (totals['walking_meters'], totals['total_minutes'], path) < (old[1]['walking_meters'], old[1]['total_minutes'], old[0]):
                    candidates[mask] = (path, totals, score)
            for j in range(n):
                if mask & (1 << j) or not allow_reorder and last != n and j <= last: continue
                distance = distances[last][j]
                if not math.isfinite(distance): continue
                new_walk, new_visits = walk+math.ceil(distance/speed), visiting+visits[j]
                if minutes is not None and new_walk+new_visits+reserve > minutes: continue
                key = (mask | (1 << j), j)
                state = (new_walk, meters+distance, path+(j,), new_visits, score+values[j])
                old = next_layer.get(key)
                if old is None or state[:3] < old[:3]: next_layer[key] = state
        if capped and len(next_layer) > 2048:
            next_layer = dict(sorted(next_layer.items(), key=lambda item: (
                -((item[0][0] & required_mask).bit_count()), -item[1][4], item[1][0], item[1][1], item[1][2]))[:2048])
        layer = next_layer
        if not layer: break
    feasible = bool(candidates)
    if feasible:
        best = max(candidates.values(), key=lambda c: (c[2], len(c[0]), -c[1]['walking_meters'], -c[1]['total_minutes']))
        if strategy == 'shortest' and best[0]:
            coverage = [c for c in candidates.values() if c[2] >= .7*best[2] and len(c[0]) >= max(1, math.ceil(.7*len(best[0])))]
            best = min(coverage, key=lambda c: (c[1]['walking_meters'], c[1]['total_minutes'], -c[2], c[0]))
        kept = [eligible[j] for j in best[0]]
    else:
        kept = [s for s in eligible if s['spot_id'] in required]
    proposed = overview(kept, avoid_steps)
    feasible = feasible and proposed['complete'] and (minutes is None or proposed['total_minutes'] <= minutes)
    chosen = {s['spot_id'] for s in kept}
    removed = []
    for s in suffix:
        if s['spot_id'] in chosen: continue
        reason = ('visitor' if s['spot_id'] in excluded else 'exit' if scenario=='exit' else
                  'stairs' if avoid_steps and _features(s)['stairs'] else
                  'routing' if not math.isfinite(distance_between(anchor, s, avoid_steps)) else
                  'less_walking' if strategy=='shortest' else 'budget')
        removed.append(dict(spot_id=s['spot_id'], spot_name=s['spot_name'], reason=reason))
    old_ids = [s['spot_id'] for s in suffix if s['spot_id'] in chosen]
    new_ids = [s['spot_id'] for s in kept]
    failure = '' if feasible else ('no_path' if not proposed['complete'] else 'required_budget' if required else 'exit_budget')
    return dict(current_spot=anchor['spot_name'], current_spot_id=anchor['spot_id'],
        original_route=original, proposed_route=proposed,
        completed_ids=[s['spot_id'] for s in route[:index]],
        spot_ids=[s['spot_id'] for s in route[:index+1]+kept],
        next_spots=[dict(spot_id=s['spot_id'], spot_name=s['spot_name']) for s in kept],
        removed=removed, totals=public_totals(proposed), original_totals=public_totals(original),
        remaining_minutes=minutes, feasible=feasible, failure_code=failure,
        pace=pace, end_area=end_area, avoid_steps=avoid_steps,
        end_anchor=NETWORK['gates'][end_area]['label'] if end_area!='auto' else '',
        exit_only=not kept, scenario=scenario, strategy=strategy,
        required_spot_ids=sorted(required), reordered=old_ids!=new_ids,
        unchanged=old_ids==new_ids and not removed and not required and
            original['total_minutes']==proposed['total_minutes'] and original['walking_meters']==proposed['walking_meters'] and
            baseline.get('end_area','auto')==end_area and baseline.get('pace','standard')==pace and
            baseline.get('avoid_steps',baseline.get('pace')=='relaxed')==avoid_steps,
        algorithm='pedestrian-subset-dp-bounded-v2' if capped else 'pedestrian-subset-dp-v2',
        network_version=network_version(), distance_version=NETWORK['snapshot_date'],
        note='沿园内步行路网计算，已计入所选出口；开放状态以现场为准，避开已标注台阶不代表无障碍认证。')
