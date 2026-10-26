"""Station context, bounded walking plans and grounded public consultation."""
import math
import re
import json
from pathlib import Path
from datetime import datetime
from .walking_network import NETWORK, access_point, anchor_distance, distance_between, network_version
from .route_presentation import route_overview
from .route_order import optimize_order

ENGLISH = json.loads((Path(__file__).resolve().parents[3]/'data/station_public_english.json').read_text(encoding='utf-8'))


def english_local_answer(spot, answer):
    translated = ENGLISH.get(answer)
    if translated: return translated
    # Prefer a published English description to an invented translation when the
    # provider is unavailable. Specific missing details remain explicitly unknown.
    description = ENGLISH.get(spot.get('description', ''))
    return (description + '\n\nFor further details, try the digital guide again or ask on-site staff.' if description else
            'A verified English explanation for this question is temporarily unavailable. You can browse the attraction information or ask on-site staff.')


def anchors():
    return {**{'gate:' + k: v for k, v in NETWORK['gates'].items()},
            **{'spot:' + k: v for k, v in NETWORK['anchors'].items()}}


def station_anchor(station):
    source = anchors().get(station.anchor_key)
    if not source:
        raise ValueError('本站步行起点尚未配置，请联系工作人员')
    return dict(source, label=station.name, label_en=station.name_en)


def plan_walk(station, spots, preferences):
    """Beam search on actual road costs; explicit choices are never dropped."""
    start = station_anchor(station)
    end = start if preferences['end_area'] == 'return' else NETWORK['gates'][preferences['end_area']]
    options = dict(pace=preferences['pace'], start_anchor=start, end_anchor=end,
                   avoid_steps=preferences['avoid_steps'])
    allowed = [s for s in spots if access_point(s)]
    requested = preferences.get('spot_ids', [])
    if requested:
        lookup = {s['spot_id']: s for s in allowed}
        if len(set(requested)) != len(requested) or any(s not in lookup for s in requested):
            raise ValueError('所选景点不可用或尚未接入本站步行路网')
        selected = [lookup[s] for s in requested]
        route = (optimize_order(selected, fixed_start=False, **options)['proposed_route']
                 if len(selected) > 1 else route_overview(selected, **options))
        if not route['complete']: raise ValueError('没有找到完整的步行路线，请调整景点或少台阶选项')
        if route['total_minutes'] > preferences['budget']:
            raise ValueError('已选景点超出时间预算，请增加时间或减少景点；系统会保留您的选择')
        return [dict(kind='custom', title='自选景点顺路方案', title_en='Your selected stops', route=route)]

    n, speed = len(allowed), 55 if preferences['pace'] == 'relaxed' else 75
    distances = [[distance_between(a, b, preferences['avoid_steps']) for b in allowed] for a in allowed]
    entry = [anchor_distance(s, start, preferences['avoid_steps']) for s in allowed]
    exit = [anchor_distance(s, end, preferences['avoid_steps']) for s in allowed]
    rest_factor = .15 if preferences['pace'] == 'relaxed' else .08
    budget = preferences['budget']
    interest = preferences['interest']
    preference_names = {
        'history': {'仁寿殿', '德和园', '玉澜堂', '乐寿堂', '排云殿', '佛香阁', '长廊'},
        'nature': {'昆明湖', '南湖岛', '谐趣园', '长廊', '玉带桥'},
        'photo': {'昆明湖', '十七孔桥', '玉带桥', '石舫', '佛香阁', '长廊'},
        'family': {'铜牛', '长廊', '昆明湖', '谐趣园', '德和园'},
    }.get(interest, set())

    def total(walk, visit): return walk + visit + math.ceil((walk + visit) * rest_factor)
    pool = []
    beam = [((), 0, 0, 0., 0)]
    # At most eight stops per automatic plan and 72 states per depth.
    for _ in range(min(n, 8)):
        candidates = []
        for path, walk, visit, utility, distance in beam:
            for i, spot in enumerate(allowed):
                if i in path: continue
                leg = distances[path[-1]][i] if path else entry[i]
                if not math.isfinite(leg) or not math.isfinite(exit[i]): continue
                next_walk = walk + math.ceil(leg / speed)
                next_visit = visit + max(1, int(spot.get('visit_duration') or 20))
                duration = total(next_walk + math.ceil(exit[i] / speed), next_visit)
                if duration > budget: continue
                score = utility + (2.4 if spot['spot_name'] in preference_names else 1.)
                state = (path + (i,), next_walk, next_visit, score, distance + leg)
                candidates.append(state)
                pool.append((state, duration, distance + leg + exit[i]))
        if not candidates: break
        candidates.sort(key=lambda s: (-(s[3] - .012 * (s[1] + s[2])), s[4], s[0]))
        beam = candidates[:72]
    if not pool: raise ValueError('当前时间不足以完成本站出发并到达终点的游览，请增加时间或更换终点')
    output, sets = [], set()
    for kind, title, title_en, weight in [('balanced', '为您推荐', 'Recommended for you', .015),
                                            ('easy', '少走一些', 'A shorter walk', .08),
                                            ('rich', '多看一些', 'More to discover', .002)]:
        ranked = sorted(pool, key=lambda p: (-(p[0][3] - weight * p[1] - (.001 * p[2] if kind == 'easy' else .0001 * p[2])), p[2], p[0][0]))
        for (path, _, _, _, _), _, _ in ranked:
            if kind == 'balanced' and len(path) > 6: continue
            if kind == 'easy' and len(path) > max(1, min(4, len(output[0]['route']['stops']) - 1)): continue
            if kind == 'rich' and len(path) <= len(output[0]['route']['stops']): continue
            membership = frozenset(path)
            if membership in sets: continue
            selected = [allowed[i] for i in path]
            route = (optimize_order(selected, fixed_start=False, **options)['proposed_route']
                     if len(selected) > 1 else route_overview(selected, **options))
            if not route['complete'] or route['total_minutes'] > budget: continue
            if kind == 'easy' and (route['walking_meters'] >= output[0]['route']['walking_meters'] or route['total_minutes'] > output[0]['route']['total_minutes']): continue
            sets.add(membership)
            output.append(dict(kind=kind, title=title, title_en=title_en, route=route))
            break
    if not output: raise ValueError('步行路网已变化，请重新规划')
    return output


def extract_request(question, existing=None):
    """Conservative bilingual hints. A visible editable form always confirms them."""
    values = dict(existing or {})
    q = re.sub(r'(?<=\w)[-–](?=hours?\b)', ' ', question.lower())
    match = re.search(r'(\d{1,3})\s*(?:分钟|minutes?|mins?)', q)
    hours = re.search(r'(\d+(?:\.\d+)?)\s*(?:个?小时|hours?|hrs?)', q)
    if match: values['budget'] = max(20, min(480, int(match[1])))
    elif hours: values['budget'] = max(20, min(480, round(float(hours[1]) * 60)))
    else:
        chinese = re.search(r'([一二两三四五六七八])个?(半)?小时', q)
        english = re.search(r'\b(one|two|three|four|five|six|seven|eight)(?:\s+and\s+a\s+(half))?\s+hours?\b', q)
        if chinese:
            count={'一':1,'二':2,'两':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8}[chinese[1]]
            values['budget']=min(480,count*60+(30 if chinese[2] else 0))
        elif english:
            count=['one','two','three','four','five','six','seven','eight'].index(english[1])+1
            values['budget']=min(480,count*60+(30 if english[2] else 0))
        elif '半小时' in q or 'half an hour' in q: values['budget'] = 30
        elif '半天' in q: values['budget'] = 240
    if any(s in q for s in ('不要台阶', '少台阶', '轮椅', 'avoid stairs', 'wheelchair')): values['avoid_steps'] = True
    for words, area in [(('东门', '东宫门', 'east gate', 'east palace gate'), 'east'), (('北门', '北宫门', 'north gate', 'north palace gate'), 'north'), (('南门', '新建宫门', 'south gate', 'new palace gate'), 'south'), (('回到这里', '返回本站', '回到本站', '回本站', 'return here', 'return to this station'), 'return')]:
        if any(w in q for w in words): values['end_area'] = area; break
    return values


def consultation(question, station, spots, language):
    from .tour_language import query_aliases
    from .tour_dialogue import resolve_turn, local_answer
    from .tour_visuals import build_visual_context
    en = language == 'en'
    q = query_aliases(question)
    spot = next((s for s in sorted(spots, key=lambda s: -len(s['spot_name'])) if s['spot_name'] in q), None)
    wayfinding = bool(spot and re.search(r'怎么走|怎么到|如何到|how\s+(?:do|can)\s+i\s+(?:get|reach)|directions|way to', q, re.I))
    route_intent = any(s in q.lower() for s in ('规划', '路线', '怎么玩', '安排', 'plan', 'route', 'itinerary')) or (
        not spot and any(s in q.lower() for s in ('小时', '分钟', 'hour', 'minutes')))
    facility_intent = any(s in q.lower() for s in ('厕所', '卫生间', '饮水', '服务台', '出口', 'restroom', 'toilet', 'water', 'exit', 'facility'))
    if wayfinding: route_intent = False
    actions = ['plan'] if route_intent else ['facilities'] if facility_intent or wayfinding else ['explore']
    visuals = None
    if wayfinding:
        from .tour_language import ENGLISH_SPOT_NAMES
        answer = ('I can show the walking path from this station to ' + ENGLISH_SPOT_NAMES.get(spot['spot_name'], 'the attraction') + '. Use the directions button below to see the route and estimated walking time.' if en else
                  '我可以为您查看从本站到' + spot['spot_name'] + '的步行路线。点击下方入口，可在地图上查看路径与预计步行时间。')
    elif route_intent:
        answer = ('Check your time and end point in the planning form. You can also select the attractions you want to visit. The route starts at this station and includes walking, visits and breaks in the time estimate.' if en else
                  '请在规划表里确认游览时间和终点，也可以直接选择想去的景点。路线从本站出发，预计用时包含步行、景点停留和休息。')
    elif facility_intent:
        answer = ('Choose a published facility or exit below to see the walking path from this station. Unverified facilities and live opening conditions cannot be assumed; please ask staff if a service is not listed.' if en else
                  '您可以在设施与出口中查看已发布的位置，并计算从本站出发的步行路线。未核实的卫生间、饮水点不会推测标注；未列出的服务请咨询现场工作人员。')
    elif spot:
        turn = resolve_turn(q, spot)
        answer, _ = local_answer(turn, spot)
        visuals = build_visual_context(spot, turn.intents, answer, language)
        actions = ['explore', 'plan']
    else:
        answer = ('I am the digital receptionist at this fixed service station. Ask about a Summer Palace attraction, plan a walk, or find a published facility or exit. For example: “Please plan a two-hour visit.”' if en else
                  '我是固定在本站的数字接待员，可以介绍颐和园景点、从这里规划游览，也能帮您查找已发布的设施与出口。您可以说：“帮我安排两小时游览。”')
    return dict(answer=answer, actions=actions, visuals=visuals, spot=spot, route_intent=route_intent,
                destination_key='spot:'+spot['spot_name'] if wayfinding else None)


def revise_plan_request(question, snapshot, spots):
    """Only explicit route edits change the saved route; ordinary questions stay read-only."""
    from .tour_language import query_aliases
    q = query_aliases(question).lower()
    original = snapshot['preferences']
    values = extract_request(q, original)
    if not re.search(r'最后|离园|改为|换.*出口|返回本站|回到这里|finish|end at|return here', q):
        values['end_area'] = original['end_area']
    if not re.search(r'我有|只有|安排|改为|控制在|预算|within|have|budget|make|set|change', q):
        values['budget'] = original['budget']
    ids = [s['spot_id'] for s in snapshot['route']['stops']]
    changed = any(values.get(k) != original.get(k) for k in ('budget', 'end_area', 'avoid_steps'))
    shorter = bool(re.search(r'太远|太长|短一点|少走|shorter|too (?:long|far)', q))
    if shorter:
        values['budget'] = max(20, min(original['budget'] - 15, snapshot['route']['total_minutes'] - 10))
        if values['budget'] >= snapshot['route']['total_minutes']:
            raise ValueError('这条路线已很短，可以直接移除不想去的景点')
        changed = True
    edited_stops = False
    # Each clause is handled independently so “remove A, add B” stays unambiguous.
    for clause in re.split(r'[，,。;；]|然后|再去|\band\b', q):
        matched = [s['spot_id'] for s in spots if s['spot_name'].lower() in clause]
        remove = bool(re.search(r"去掉|删掉|移除|不去|不要去|不想去|不想看|不看|remove|skip|drop|don't want to visit|do not want to visit", clause))
        add = bool(re.search(r'加上|加入|增加|还想去|也想去|想去|add|include|want to visit', clause))
        if matched and (remove or add):
            edited_stops = changed = True
            ids = [i for i in ids if i not in matched] if remove else list(dict.fromkeys(ids + matched))
    if not changed:
        return None
    if edited_stops and not ids:
        raise ValueError('路线至少保留一个景点，请先加入其他景点')
    # A shorter automatic itinerary may choose fewer stops. Explicit selections stay pinned.
    values['spot_ids'] = ids if edited_stops or not shorter else list(original.get('spot_ids', []))
    return values
