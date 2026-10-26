"""Reorder a complete selection over the pedestrian graph, never drop a stop."""
from array import array
import math

from .route_presentation import route_overview
from .walking_network import distance_between, gate_distance, anchor_distance, network_version

INF = (1 << 63) - 1


def _exact_order(vertices, head, tail, edges, entry, exit):
    """Held–Karp on movable stops; endpoints and gate costs are included."""
    n = len(vertices)
    if not n:
        return ([head] if head is not None else []) + ([tail] if tail is not None else [])
    size = (1 << n) * n
    costs = array('q', [INF]) * size
    parents = array('b', [-1]) * size
    for i, vertex in enumerate(vertices):
        costs[(1 << i) * n + i] = edges[head][vertex] if head is not None else entry[vertex]
    full = (1 << n) - 1
    for mask in range(1, full + 1):
        last_bits = mask
        remaining = full ^ mask
        while last_bits:
            bit = last_bits & -last_bits
            last_bits -= bit
            i = bit.bit_length() - 1
            current = costs[mask * n + i]
            if current == INF:
                continue
            next_bits = remaining
            row = edges[vertices[i]]
            while next_bits:
                nxt = next_bits & -next_bits
                next_bits -= nxt
                j = nxt.bit_length() - 1
                edge = row[vertices[j]]
                if edge == INF:
                    continue
                offset = (mask | nxt) * n + j
                candidate = current + edge
                if candidate < costs[offset]:
                    costs[offset], parents[offset] = candidate, i
    best, last = INF, -1
    for i, vertex in enumerate(vertices):
        suffix = edges[vertex][tail] if tail is not None else exit[vertex]
        total = costs[full * n + i] + suffix
        if total < best:
            best, last = total, i
    if last < 0:
        raise ValueError('所选景点没有完整的步行路径，暂时无法优化顺序')
    ordered, mask = [], full
    while last >= 0:
        ordered.append(vertices[last])
        previous = parents[mask * n + last]
        mask ^= 1 << last
        last = previous
    return ([head] if head is not None else []) + ordered[::-1] + ([tail] if tail is not None else [])


def _bounded_order(vertices, head, tail, edges, entry, exit, original):
    """Deterministic multistart + 2-opt for >16 movable stops, bounded to 20."""
    def cost(path):
        return entry[path[0]] + sum(edges[a][b] for a, b in zip(path, path[1:])) + exit[path[-1]]

    best, best_cost = original[:], cost(original)
    for seed in vertices:
        path = [head] if head is not None else []
        path.append(seed)
        remaining = set(vertices) - {seed}
        while remaining:
            nxt = min(remaining, key=lambda v: (edges[path[-1]][v], v))
            path.append(nxt)
            remaining.remove(nxt)
        if tail is not None:
            path.append(tail)
        low, high = int(head is not None), len(path) - int(tail is not None)
        # Strict improvements only: deterministic and cannot oscillate.
        for _ in range(12):
            current = cost(path)
            candidate, candidate_cost = path, current
            for a in range(low, high - 1):
                for b in range(a + 2, high + 1):
                    proposed = path[:a] + path[a:b][::-1] + path[b:]
                    value = cost(proposed)
                    if value < candidate_cost:
                        candidate, candidate_cost = proposed, value
            if candidate_cost >= current:
                break
            path = candidate
        value = cost(path)
        if value < best_cost:
            best, best_cost = path, value
    return best


def optimize_order(spots, *, fixed_start=True, fixed_end=False, pace='standard',
                   start_area='auto', end_area='auto', avoid_steps=False, reserve=0, start_anchor=None, end_anchor=None):
    if not 2 <= len(spots) <= 20:
        raise ValueError('请选择2至20个景点再优化顺序')
    ids = [s['spot_id'] for s in spots]
    if len(set(ids)) != len(ids):
        raise ValueError('路线中有重复景点')
    version = network_version()
    options = dict(pace=pace, start_area=start_area, end_area=end_area,
                   avoid_steps=avoid_steps, reserve=reserve)
    if start_anchor: options['start_anchor'] = start_anchor
    if end_anchor: options['end_anchor'] = end_anchor
    original = route_overview(spots, **options)
    if not original['complete']:
        raise ValueError('所选景点没有完整的步行路径，暂时无法优化顺序')
    n, speed = len(spots), 55 if pace == 'relaxed' else 75
    distances = [[distance_between(a, b, avoid_steps) for b in spots] for a in spots]
    starts = [anchor_distance(s, start_anchor, avoid_steps) if start_anchor else gate_distance(s, start_area, avoid_steps) if start_area != 'auto' else 0 for s in spots]
    ends = [anchor_distance(s, end_anchor, avoid_steps) if end_anchor else gate_distance(s, end_area, avoid_steps) if end_area != 'auto' else 0 for s in spots]
    finite = [m for row in distances for m in row if math.isfinite(m)] + [m for m in starts + ends if math.isfinite(m)]
    # A metre dominates every possible rounded walking-minute tie breaker.
    base = (n + 1) * math.ceil(max(finite, default=0) / speed) + 1

    def encode(meters):
        return int(meters) * base + math.ceil(meters / speed) if math.isfinite(meters) else INF

    edges = [[encode(m) for m in row] for row in distances]
    entry, exit = [encode(m) for m in starts], [encode(m) for m in ends]
    head, tail = (0 if fixed_start else None), (n - 1 if fixed_end else None)
    vertices = [i for i in range(n) if i not in (head, tail)]
    exact = len(vertices) <= 16
    order = (_exact_order(vertices, head, tail, edges, entry, exit) if exact else
             _bounded_order(vertices, head, tail, edges, entry, exit, list(range(n))))
    proposed = route_overview([spots[i] for i in order], **options)
    # Metres and rounded total minutes must both not increase. On ties prefer
    # the visitor's original order, avoiding a cosmetic, zero-benefit shuffle.
    improved = (proposed['complete'] and
                proposed['walking_meters'] <= original['walking_meters'] and
                proposed['total_minutes'] <= original['total_minutes'] and
                (proposed['walking_meters'], proposed['total_minutes']) <
                (original['walking_meters'], original['total_minutes']))
    optimal = exact
    if not improved:
        optimal = exact and (proposed['walking_meters'], proposed['walking_minutes']) == (
            original['walking_meters'], original['walking_minutes'])
        order, proposed = list(range(n)), original
    if network_version() != version:
        raise ValueError('步行路网已变化，请重新计算')
    return dict(input_spot_ids=ids, spot_ids=[ids[i] for i in order], original_route=original,
                proposed_route=proposed, unchanged=not improved, optimal=optimal,
                method='exact' if exact else 'multistart_2opt',
                saved_meters=original['walking_meters'] - proposed['walking_meters'],
                saved_minutes=original['total_minutes'] - proposed['total_minutes'],
                fixed_start=fixed_start, fixed_end=fixed_end, network_version=version)
