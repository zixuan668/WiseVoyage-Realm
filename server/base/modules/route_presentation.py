"""Shared route geometry, distance and timing from the local pedestrian graph."""
import math
from .walking_network import route_between, access_point, network_version, NETWORK


def route_overview(spots, pace='standard', include_first_visit=True, end_area='auto', avoid_steps=False, reserve=0, start_area='auto', start_anchor=None, end_anchor=None):
    speed = 55 if pace == 'relaxed' else 75
    stops = []
    for index, spot in enumerate(spots):
        lat, lng = spot.get('latitude'), spot.get('longitude')
        valid = (isinstance(lat, (int, float)) and isinstance(lng, (int, float))
                 and math.isfinite(lat) and math.isfinite(lng) and -90 <= lat <= 90
                 and -180 <= lng <= 180 and bool(lat) and bool(lng))
        anchor = access_point(spot)
        stops.append(dict(spot_id=spot['spot_id'], spot_name=spot['spot_name'], order=index+1,
            latitude=lat if valid else None, longitude=lng if valid else None,
            access_latitude=anchor['latitude'] if anchor else None,
            access_longitude=anchor['longitude'] if anchor else None,
            access_label=anchor['label'] if anchor else '',
            access_offset_meters=anchor['offset_meters'] if anchor else None,
            visit_minutes=max(1, int(spot.get('visit_duration') or 10)) if index or include_first_visit else 0))

    def leg(a, b=None, gate=None, anchor=None):
        path = route_between(a, b, end_area=gate, avoid_steps=avoid_steps, destination_anchor=anchor)
        return dict(from_id=a['spot_id'], to_id=b['spot_id'] if b else 0,
            from_name=a['spot_name'], to_name=b['spot_name'] if b else (anchor or NETWORK['gates'][gate])['label'],
            meters=path['meters'] if path else None,
            minutes=math.ceil(path['meters']/speed) if path else None,
            basis='osm_pedestrian_network' if path else 'unavailable',
            geometry=path['geometry'] if path else [],
            sections=path['sections'] if path else [],
            has_steps=path['has_steps'] if path else None,
            steps_meters=path['steps_meters'] if path else None,
            available=path is not None, is_exit=bool(gate or anchor))

    legs = [leg(a, b) for a, b in zip(spots, spots[1:])]
    entry_anchor = start_anchor or NETWORK['gates'].get(start_area)
    entry_leg = leg(spots[0], anchor=entry_anchor) if spots and entry_anchor else None
    if entry_leg:
        entry_leg.update(from_id=0, to_id=spots[0]['spot_id'], from_name=entry_anchor['label'],
            to_name=spots[0]['spot_name'], geometry=list(reversed(entry_leg['geometry'])),
            sections=list(reversed(entry_leg['sections'])), is_exit=False, is_entry=True)
        if entry_anchor.get('label_en'): entry_leg['from_name_en'] = entry_anchor['label_en']
    gate = end_anchor or NETWORK['gates'].get(end_area)
    exit_leg = leg(spots[-1], anchor=gate) if spots and gate else None
    if exit_leg and gate.get('label_en'): exit_leg['to_name_en'] = gate['label_en']
    all_legs = ([entry_leg] if entry_leg else []) + legs + ([exit_leg] if exit_leg else [])
    complete = all(x['available'] for x in all_legs) and all(s['access_latitude'] is not None for s in stops)
    visit = sum(x['visit_minutes'] for x in stops)
    walk = sum(x['minutes'] or 0 for x in legs) + ((entry_leg['minutes'] or 0) if entry_leg else 0)
    exit_time = (exit_leg['minutes'] or 0) if exit_leg else 0
    rest = math.ceil((visit+walk+exit_time)*(.15 if pace=='relaxed' else .08)) if stops else 0
    return dict(stops=stops, legs=legs, pace=pace, complete=complete,
        walking_meters=sum(x['meters'] or 0 for x in all_legs) if complete else None,
        walking_minutes=walk if complete else None, visit_minutes=visit, rest_minutes=rest,
        exit_minutes=exit_time if complete else None, reserve_minutes=reserve,
        total_minutes=visit+walk+exit_time+rest+reserve if complete else None,
        exit_leg=exit_leg, exit_anchor=gate, avoid_steps=avoid_steps,
        entry_leg=entry_leg, entry_anchor=entry_anchor,
        distance_version=NETWORK['snapshot_date'], network_version=network_version(),
        geometry='pedestrian_paths', missing_legs=sum(not x['available'] for x in all_legs),
        note='沿 OSM 园内步行路网计算；接入点为景点附近步道。未接入实时开放信息，不构成无障碍认证。')
