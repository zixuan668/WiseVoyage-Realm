import asyncio
import math
import unittest
from unittest.mock import patch

from server.base.modules import walking_network as roads
from server.base.modules.route_presentation import route_overview
from server.base.modules.adaptive_itinerary import repair_route
from server.base.modules.route_recommender import recommend_route
from test_preference_planner import SPOTS

BY_NAME = {s['spot_name']: s for s in SPOTS}


class WalkingNetworkTests(unittest.TestCase):
    def test_all_scenic_pairs_follow_source_edges_and_share_distance_geometry(self):
        pairs = {frozenset((e['a'], e['b'])) for e in roads.NETWORK['edges']}
        for a in SPOTS:
            for b in SPOTS:
                route = roads.route_between(a, b)
                self.assertIsNotNone(route)
                ids = route['node_ids']
                self.assertEqual(route['geometry'], [list(roads.NODES[i]) for i in ids])
                self.assertTrue(all(frozenset((x,y)) in pairs for x,y in zip(ids,ids[1:])))
                length = sum(roads.haversine(x,y) for x,y in zip(route['geometry'],route['geometry'][1:]))
                self.assertAlmostEqual(length, route['meters'], delta=1)

    def test_lake_detour_cannot_be_replaced_by_a_straight_line(self):
        a,b = BY_NAME['玉带桥'], BY_NAME['铜牛']
        path = roads.route_between(a,b)
        direct = roads.haversine([a['latitude'],a['longitude']], [b['latitude'],b['longitude']])
        self.assertGreater(path['meters'],direct*1.8)
        self.assertGreater(len(path['geometry']),15)

    def test_closed_bridge_disconnects_island_instead_of_fabricating_a_link(self):
        a,b = BY_NAME['南湖岛'], BY_NAME['铜牛']
        self.assertIsNotNone(roads.route_between(a,b))
        with patch.object(roads,'rules',return_value=(187196435,)):
            self.assertIsNone(roads.route_between(a,b))
            view=route_overview([a,b])
            self.assertFalse(view['complete'])
            self.assertEqual(view['legs'][0]['geometry'],[])
            self.assertIsNone(view['total_minutes'])

    def test_avoidance_applies_to_road_segments_not_just_spot_labels(self):
        a,b=BY_NAME['仁寿殿'],BY_NAME['苏州街']
        self.assertTrue(roads.route_between(a,b)['has_steps'])
        self.assertIsNone(roads.route_between(a,b,avoid_steps=True))
        safe=roads.route_between(BY_NAME['长廊'],BY_NAME['昆明湖'],avoid_steps=True)
        self.assertIsNotNone(safe)
        self.assertFalse(safe['has_steps'])

    def test_gate_is_an_osm_entrance_and_exit_time_has_no_artificial_five_minutes(self):
        a=BY_NAME['昆明湖']
        view=route_overview([a],include_first_visit=False,end_area='east')
        self.assertEqual(view['exit_anchor']['source_node_id'],3485506925)
        self.assertEqual(view['exit_leg']['geometry'][-1],list(roads.NODES[view['exit_anchor']['node_id']]))
        self.assertEqual(view['exit_minutes'],math.ceil(view['exit_leg']['meters']/75))
        self.assertEqual(view['walking_meters'],view['exit_leg']['meters'])

    def test_namesake_or_moved_poi_has_no_fake_path(self):
        for a in [dict(BY_NAME['长廊'],city='上海'),dict(BY_NAME['长廊'],latitude=31.2)]:
            self.assertIsNone(roads.route_between(a,BY_NAME['昆明湖']))

    def test_access_points_and_display_points_remain_separate(self):
        point=BY_NAME['仁寿殿']
        view=route_overview([point])['stops'][0]
        self.assertEqual(view['latitude'],point['latitude'])
        self.assertNotEqual(view['latitude'],view['access_latitude'])
        self.assertLess(view['access_offset_meters'],80)

    def test_planner_and_preview_share_entry_exit_road_times(self):
        plan=asyncio.run(recommend_route(['nature','photography'],SPOTS,180,'北京','standard','east','south',10))
        spots=[next(s for s in SPOTS if s['spot_id']==sid) for sid in plan['spot_ids']]
        view=route_overview(spots,plan['pace'],start_area='east',end_area='south',reserve=10,avoid_steps=plan['avoid_steps'])
        self.assertTrue(view['complete'])
        self.assertEqual(view['total_minutes'],plan['estimated_time_minutes'])
        self.assertEqual(view['walking_minutes'],plan['walking_time_minutes'])
        self.assertEqual(view['exit_minutes'],plan['exit_time_minutes'])


class ImprovedRepairTests(unittest.TestCase):
    def test_reordering_reduces_backtracking_without_dropping_required_stops(self):
        route=[BY_NAME[n] for n in ['仁寿殿','铜牛','石舫','谐趣园','昆明湖','十七孔桥']]
        original=repair_route(route,0,SPOTS,None,end_area='east')
        result=repair_route(route,0,SPOTS,None,end_area='east',allow_reorder=True,required=[s['spot_id'] for s in route[1:]])
        self.assertTrue(result['feasible'])
        self.assertTrue(result['reordered'])
        self.assertEqual(set(result['spot_ids']),set(original['spot_ids']))
        self.assertLess(result['totals']['walking_meters'],original['totals']['walking_meters'])
        self.assertEqual(result['spot_ids'][0],route[0]['spot_id'])

    def test_conflicting_or_unaffordable_must_visit_is_not_silently_removed(self):
        route=[BY_NAME[n] for n in ['仁寿殿','长廊','昆明湖']]
        sid=route[-1]['spot_id']
        with self.assertRaises(ValueError):repair_route(route,0,SPOTS,120,required=[sid],excluded=[sid])
        result=repair_route(route,0,SPOTS,1,required=[sid],allow_reorder=True)
        self.assertFalse(result['feasible'])
        self.assertEqual(result['failure_code'],'required_budget')

    def test_direct_exit_does_not_keep_future_attractions_or_require_a_time_limit(self):
        route=[BY_NAME[n] for n in ['仁寿殿','长廊','昆明湖','十七孔桥']]
        result=repair_route(route,1,SPOTS,None,end_area='south',scenario='exit',allow_reorder=True)
        self.assertTrue(result['feasible'])
        self.assertEqual(result['spot_ids'],[route[0]['spot_id'],route[1]['spot_id']])
        self.assertEqual(result['next_spots'],[])
        self.assertEqual(result['end_anchor'],'新建宫门')
        self.assertGreater(len(result['proposed_route']['exit_leg']['geometry']),5)

    def test_less_walking_plan_has_a_meaningful_retention_floor(self):
        route=[BY_NAME[n] for n in ['仁寿殿','铜牛','石舫','谐趣园','昆明湖','十七孔桥']]
        highlights=repair_route(route,0,SPOTS,None,allow_reorder=True,strategy='highlights')
        shorter=repair_route(route,0,SPOTS,None,allow_reorder=True,strategy='shortest')
        self.assertGreaterEqual(len(shorter['next_spots']),math.ceil(.7*len(highlights['next_spots'])))
        self.assertLessEqual(shorter['totals']['walking_meters'],highlights['totals']['walking_meters'])

    def test_before_comparison_uses_saved_gate_pace_and_reserve(self):
        route=[BY_NAME[n] for n in ['仁寿殿','长廊','昆明湖']]
        saved=dict(pace='standard',end_area='east',reserve_minutes=9)
        before=route_overview(route,include_first_visit=False,end_area='east',reserve=9)
        result=repair_route(route,0,SPOTS,None,pace='relaxed',end_area='north',reserve=3,
            scenario='exit',avoid_steps=False,original_plan=saved)
        self.assertEqual(result['original_totals']['total_minutes'],before['total_minutes'])
        self.assertEqual(result['original_totals']['walking_meters'],before['walking_meters'])
        self.assertEqual(result['original_totals']['reserve_minutes'],9)
        self.assertEqual(result['original_route']['exit_anchor']['label'],'东宫门')
        self.assertEqual(result['proposed_route']['exit_anchor']['label'],'北宫门')

    def test_late_tour_progress_preserves_full_completed_prefix(self):
        route=SPOTS[:7]
        p=repair_route(route,3,SPOTS,100,allow_reorder=True,end_area='east',excluded=[route[-1]['spot_id']])
        self.assertEqual(p['spot_ids'][:4],[s['spot_id'] for s in route[:4]])
        self.assertEqual(len(p['spot_ids']),len(set(p['spot_ids'])))


if __name__=='__main__':unittest.main()
