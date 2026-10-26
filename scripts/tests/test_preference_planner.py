"""Run: python -m unittest discover -s scripts/tests -p test_preference_planner.py"""
import asyncio
import json
import unittest
from pathlib import Path
from server.base.modules.route_recommender import recommend_route, WALKS, parse_preferences_from_message, parse_time_budget_from_message, get_spot_profile, verified_model_summary

ROOT=Path(__file__).resolve().parents[2]
LOCATIONS=json.loads((ROOT/'data/summer_palace_locations.json').read_text(encoding='utf-8'))['spots']
DURATIONS=[18,25,30,35,20,28,22,15,22,30,15,15,25,12,25,15]
SPOTS=[dict(spot_id=i+1,spot_name=name,city='北京',visit_duration=duration,**point) for i,((name,point),duration) in enumerate(zip(LOCATIONS.items(),DURATIONS))]

def plan(preferences,budget=120,**kwargs):return asyncio.run(recommend_route(preferences,SPOTS,budget,**kwargs))

class PreferencePlannerTests(unittest.TestCase):
    def test_unspecified_city_uses_a_feasible_plan(self):
        oversized=[dict(spot_id=100+i,spot_name=f'公园{i}',city='成都',category='natural',tags='自然',latitude=30.6,longitude=104.0,visit_duration=360) for i in range(20)]
        result=asyncio.run(recommend_route(['family','nature'],oversized+SPOTS,120))
        self.assertEqual(result['city'],'北京')
        self.assertTrue(result['spot_ids'])
        self.assertLessEqual(result['estimated_time_minutes'],120)

    def test_distinct_preferences_have_distinct_itineraries(self):
        plans=[plan([p]) for p in ['history','nature','photography','family']]
        self.assertEqual(len({tuple(sorted(p['spot_ids'])) for p in plans}),4)
        self.assertIn('玉澜堂',plans[0]['spot_names'])
        self.assertIn('南湖岛',plans[1]['spot_names'])
        self.assertIn('玉带桥',plans[2]['spot_names'])
        for p in plans:
            self.assertTrue(all(d['reason'] for d in p['score_details']))
            self.assertLess(p['spot_count'],len(SPOTS))

    def test_budget_counts_walk_and_rest(self):
        for budget in [60,90,120,180,240]:
            for preferences in [['history'],['nature'],['family'],['nature','photography']]:
                p=plan(preferences,budget,start_area='east')
                self.assertEqual(p['estimated_time_minutes'],p['visit_time_minutes']+p['walking_time_minutes']+p['rest_time_minutes'])
                self.assertLessEqual(p['estimated_time_minutes'],budget)
                self.assertGreater(p['walking_time_minutes'],0)
        self.assertGreater(plan(['nature'],240,start_area='east')['spot_count'],plan(['nature'],60,start_area='east')['spot_count'])

    def test_family_and_relaxed_avoid_stair_spots(self):
        for p in [plan(['family']),plan(['history'],240,pace='relaxed')]:
            self.assertTrue({'佛香阁','排云殿','苏州街','玉带桥'}.isdisjoint(p['spot_names']))
            self.assertEqual(p['stairs_excluded_count'],4)

    def test_lake_crossing_is_not_straight_line(self):
        self.assertGreater(WALKS['distances_meters']['铜牛']['玉带桥'],3000)
        self.assertLess(WALKS['distances_meters']['十七孔桥']['南湖岛'],500)
        for a in LOCATIONS:
            self.assertLessEqual(WALKS['anchors'][a]['snap_meters'],150)
            for b in LOCATIONS:
                self.assertEqual(WALKS['distances_meters'][a][b],WALKS['distances_meters'][b][a])

    def test_city_and_namesake_are_guarded(self):
        self.assertEqual(plan(['nature'],city='上海')['spot_ids'],[])
        other=dict(SPOTS[0],city='上海',latitude=31.23,longitude=121.47)
        self.assertIsNone(get_spot_profile(other))

    def test_comprehensive_is_exclusive_and_short_budget_honest(self):
        self.assertEqual(plan(['nature','comprehensive'])['preferences'],['comprehensive'])
        p=asyncio.run(recommend_route(['nature'],[SPOTS[3]],15))
        self.assertEqual(p['spot_ids'],[])
        self.assertEqual(p['estimated_time_minutes'],0)

    def test_language_time_and_negation(self):
        self.assertEqual(parse_preferences_from_message('不喜欢历史，想拍照'),['photography'])
        self.assertEqual(parse_time_budget_from_message('玩两个小时半'),150)
        self.assertEqual(parse_time_budget_from_message('90分钟'),90)

    def test_model_cannot_override_plan_or_introduce_an_unselected_spot(self):
        result=plan(['nature'])
        payload={'spot_ids':result['spot_ids'],'estimated_time_minutes':result['estimated_time_minutes'],'summary':'沿湖岸观察水面与园林建筑。'}
        self.assertIsNotNone(verified_model_summary(result,payload,list(LOCATIONS)))
        self.assertIsNone(verified_model_summary(result,dict(payload,spot_ids=[1,2,3]),list(LOCATIONS)))
        self.assertIsNone(verified_model_summary(result,dict(payload,estimated_time_minutes=999),list(LOCATIONS)))
        self.assertIsNone(verified_model_summary(result,dict(payload,summary='去仁寿殿看宫廷院落'),list(LOCATIONS)))

if __name__=='__main__':unittest.main()
