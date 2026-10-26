"""Build a reproducible, attributed pedestrian graph from an OSM XML export.

No invented road edges: access points split an existing OSM segment. Display POIs
remain unchanged. Run with --osm work_dirs/summer-palace-osm.xml.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SOURCE = 'https://api.openstreetmap.org/api/0.6/map?bbox=116.245,39.979,116.281,40.004'


def meters(a, b):
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    return 12742000 * math.asin(min(1, math.sqrt(math.sin((lat2-lat1)/2)**2 +
        math.cos(lat1)*math.cos(lat2)*math.sin((lon2-lon1)/2)**2)))


def inside(point, polygon):
    y, x = point
    result = False
    for (ay, ax), (by, bx) in zip(polygon, polygon[1:] + polygon[:1]):
        if (ay > y) != (by > y) and x < (bx-ax)*(y-ay)/(by-ay)+ax:
            result = not result
    return result


def project(p, a, b):
    scale = math.cos(math.radians(p[0]))
    dy, dx = b[0]-a[0], (b[1]-a[1])*scale
    den = dy*dy+dx*dx
    t = max(0, min(1, ((p[0]-a[0])*dy+(p[1]-a[1])*scale*dx)/den)) if den else 0
    q = (a[0]+t*(b[0]-a[0]), a[1]+t*(b[1]-a[1]))
    return meters(p, q), t, q


def build(path, snapshot_date):
    root = ET.parse(path).getroot()
    nodes = {int(n.attrib['id']): [float(n.attrib['lat']), float(n.attrib['lon'])] for n in root.findall('node')}
    node_tags = {int(n.attrib['id']): {t.attrib['k']: t.attrib['v'] for t in n.findall('tag')} for n in root.findall('node')}
    ways = [(int(w.attrib['id']), [int(n.attrib['ref']) for n in w.findall('nd')],
             {t.attrib['k']: t.attrib['v'] for t in w.findall('tag')}) for w in root.findall('way')]
    boundary = next(seq for _, seq, t in ways if t.get('name') == '颐和园' and t.get('leisure') == 'park')
    polygon = [nodes[n] for n in boundary]
    allowed = {'footway', 'pedestrian', 'path', 'steps', 'service', 'living_street', 'track', 'residential', 'unclassified'}
    segments = []
    for wid, seq, tags in ways:
        if tags.get('highway') not in allowed: continue
        if tags.get('foot') in {'no', 'private', 'use_sidepath'}: continue
        if tags.get('access') in {'no', 'private', 'customers', 'permit'} and tags.get('foot') not in {'yes', 'designated', 'permissive'}: continue
        if tags.get('construction') or tags.get('proposed'): continue
        for a, b in zip(seq, seq[1:]):
            if a not in nodes or b not in nodes or a == b: continue
            midpoint = [(nodes[a][i]+nodes[b][i])/2 for i in (0, 1)]
            if not inside(midpoint, polygon): continue
            if any(node_tags.get(n, {}).get('barrier') in {'wall', 'fence', 'hedge'} for n in (a, b)): continue
            if any(node_tags.get(n, {}).get('foot') == 'no' for n in (a, b)): continue
            segments.append(dict(a=a, b=b, way_id=wid, name=tags.get('name', ''),
                highway=tags['highway'], steps=tags['highway']=='steps',
                bridge=tags.get('bridge', 'no') != 'no', surface=tags.get('surface', ''),
                incline=tags.get('incline', ''), access=tags.get('foot', tags.get('access', 'unspecified')),
                covered=tags.get('covered') == 'yes'))
    spots = json.loads((ROOT/'data/summer_palace_locations.json').read_text(encoding='utf-8'))['spots']
    gate_defs = {'east': ('东宫门', 3485506925), 'north': ('北宫门', 1423042673), 'south': ('新建宫门', 4116308192)}
    anchors, gates, splits = {}, {}, {}
    targets = [(name, (v['latitude'], v['longitude']), anchors, '景点附近步道接入点') for name, v in spots.items()]
    targets += [(key, nodes[nid], gates, label) for key, (label, nid) in gate_defs.items()]
    for index, (name, point, dest, label) in enumerate(targets):
        distance, edge_index, fraction, position = min((distance, i, fraction, q)
            for i, e in enumerate(segments) for distance, fraction, q in [project(point, nodes[e['a']], nodes[e['b']])])
        if distance > 80: raise ValueError(f'{name}: access point requires review ({distance:.1f} m)')
        edge = segments[edge_index]
        if fraction < 1e-7: nid = edge['a']
        elif fraction > 1-1e-7: nid = edge['b']
        else:
            nid = -index-1
            nodes[nid] = [round(v, 8) for v in position]
            splits.setdefault(edge_index, []).append((fraction, nid))
        dest[name] = dict(node_id=nid, latitude=nodes[nid][0], longitude=nodes[nid][1],
            label=label, offset_meters=round(distance, 1), source_way_id=edge['way_id'],
            source_node_id=gate_defs[name][1] if dest is gates else None)
    edges = []
    for i, edge in enumerate(segments):
        sequence = [edge['a']] + [nid for _, nid in sorted(splits.get(i, []))] + [edge['b']]
        for a, b in zip(sequence, sequence[1:]):
            length = meters(nodes[a], nodes[b])
            if length < .01: continue
            edges.append(dict(edge, a=a, b=b, meters=round(length, 3)))
    used = {n for e in edges for n in (e['a'], e['b'])}
    graph = dict(schema=1, snapshot_date=snapshot_date, source='OpenStreetMap contributors',
        license='ODbL-1.0', license_url='https://www.openstreetmap.org/copyright', source_url=SOURCE,
        source_sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest(), coordinate_system='WGS84',
        scope='OSM 颐和园园界内的已绘制步行路段；不包含船渡或实时开放信息。',
        nodes={str(n): nodes[n] for n in sorted(used)}, edges=edges, anchors=anchors, gates=gates,
        boundary=polygon,
        limitations=['接入点来自道路投影，未做实地测绘。', '未标注台阶、临时封闭和现场管制可能缺失；不构成无障碍认证。'])
    graph['version'] = hashlib.sha256(json.dumps(graph, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16]
    return graph


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--osm', type=Path, required=True)
    parser.add_argument('--date', default='2026-10-16')
    parser.add_argument('--output', type=Path, default=ROOT/'data/summer_palace_walk_network.json')
    args = parser.parse_args()
    data = build(args.osm, args.date)
    args.output.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':'))+'\n', encoding='utf-8')
    print(f"Built {len(data['nodes'])} nodes, {len(data['edges'])} road segments, {len(data['anchors'])} access points, {len(data['gates'])} gates.")
    for name, anchor in data['anchors'].items(): print(name, anchor['offset_meters'], 'm', anchor['source_way_id'])
