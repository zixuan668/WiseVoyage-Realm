"""Local pedestrian routing. Geometry and distance come from the same OSM edges.

No straight-line fallback, synthetic road links, ferry edges, or online dependency.
OSM access/steps are map evidence, not a guarantee of live opening/accessibility.
"""
from functools import lru_cache
import hashlib
import heapq
import json
import math
from pathlib import Path

DATA = Path(__file__).resolve().parents[3]/'data'
NETWORK = json.loads((DATA/'summer_palace_walk_network.json').read_text(encoding='utf-8'))
LOCATIONS = json.loads((DATA/'summer_palace_locations.json').read_text(encoding='utf-8'))['spots']
RULES_PATH = DATA/'summer_palace_walk_rules.json'
NODES = {int(k): tuple(v) for k, v in NETWORK['nodes'].items()}
ADJ = {n: [] for n in NODES}
for index, edge in enumerate(NETWORK['edges']):
    ADJ[edge['a']].append((edge['b'], index))
    ADJ[edge['b']].append((edge['a'], index))


def rules():
    data = json.loads(RULES_PATH.read_text(encoding='utf-8'))
    blocked = data.get('blocked_way_ids')
    if not isinstance(blocked, list) or any(type(x) is not int or x <= 0 for x in blocked):
        raise ValueError('步行路网封闭配置无效，请联系管理员')
    return tuple(sorted(set(blocked)))


def network_version():
    return NETWORK['version']+'-'+hashlib.sha256(json.dumps(rules()).encode()).hexdigest()[:10]


def haversine(a, b):
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    return 12742000*math.asin(min(1, math.sqrt(math.sin((lat2-lat1)/2)**2+
        math.cos(lat1)*math.cos(lat2)*math.sin((lon2-lon1)/2)**2)))


def access_point(spot):
    name = spot.get('spot_name', '') if isinstance(spot, dict) else getattr(spot, 'spot_name', '')
    city = spot.get('city', '') if isinstance(spot, dict) else getattr(spot, 'city', '')
    if city and city not in ('北京', '北京市', 'Beijing'): return None
    source = LOCATIONS.get(name)
    if not source: return None
    try:
        value = lambda key: spot.get(key) if isinstance(spot, dict) else getattr(spot, key)
        coord = [float(value('latitude')), float(value('longitude'))]
        if not all(math.isfinite(v) for v in coord): return None
        if haversine(coord, [source['latitude'], source['longitude']]) > 150: return None
    except (TypeError, ValueError, AttributeError): return None
    return NETWORK['anchors'].get(name)


@lru_cache(maxsize=8192)
def _path(start, end, avoid_steps, blocked):
    if start not in ADJ or end not in ADJ: return None
    distances = {start: 0.0}
    previous = {}
    queue = [(0.0, start)]
    blocked = set(blocked)
    while queue:
        distance, node = heapq.heappop(queue)
        if distance != distances.get(node): continue
        if node == end: break
        for next_node, edge_index in ADJ[node]:
            edge = NETWORK['edges'][edge_index]
            if edge['way_id'] in blocked or avoid_steps and edge['steps']: continue
            candidate = distance+edge['meters']
            if candidate < distances.get(next_node, float('inf')):
                distances[next_node] = candidate
                previous[next_node] = (node, edge_index)
                heapq.heappush(queue, (candidate, next_node))
    if end not in distances: return None
    vertices, edges, current = [end], [], end
    while current != start:
        current, edge_index = previous[current]
        vertices.append(current); edges.append(edge_index)
    return tuple(reversed(vertices)), tuple(reversed(edges)), distances[end]


def route_between(a, b=None, *, end_area=None, avoid_steps=False, origin_anchor=None, destination_anchor=None):
    origin = origin_anchor or access_point(a)
    destination = destination_anchor or (NETWORK['gates'].get(end_area) if end_area else access_point(b) if b else None)
    if not origin or not destination: return None
    result = _path(origin['node_id'], destination['node_id'], bool(avoid_steps), rules())
    if result is None: return None
    vertices, indices, distance = result
    sections = []
    for index in indices:
        edge = NETWORK['edges'][index]
        if sections and sections[-1]['way_id'] == edge['way_id']:
            sections[-1]['meters'] += edge['meters']
        else:
            sections.append(dict(way_id=edge['way_id'], road_name=edge['name'], highway=edge['highway'],
                                 meters=edge['meters'], steps=edge['steps'], bridge=edge['bridge']))
    for section in sections: section['meters'] = round(section['meters'])
    return dict(meters=round(distance), geometry=[list(NODES[n]) for n in vertices],
        node_ids=list(vertices), sections=sections,
        has_steps=any(NETWORK['edges'][i]['steps'] for i in indices),
        steps_meters=round(sum(NETWORK['edges'][i]['meters'] for i in indices if NETWORK['edges'][i]['steps'])),
        origin=dict(origin), destination=dict(destination), basis='osm_pedestrian_network')


def distance_between(a, b, avoid_steps=False):
    origin, destination = access_point(a), access_point(b)
    result = _path(origin['node_id'], destination['node_id'], bool(avoid_steps), rules()) if origin and destination else None
    return round(result[2]) if result else float('inf')


def gate_distance(a, area, avoid_steps=False):
    origin, destination = access_point(a), NETWORK['gates'].get(area)
    result = _path(origin['node_id'], destination['node_id'], bool(avoid_steps), rules()) if origin and destination else None
    return round(result[2]) if result else float('inf')


def anchor_distance(a, anchor, avoid_steps=False):
    origin = access_point(a)
    result = _path(origin['node_id'], anchor['node_id'], bool(avoid_steps), rules()) if origin and anchor else None
    return round(result[2]) if result else float('inf')
