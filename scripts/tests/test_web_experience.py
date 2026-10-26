import unittest
from server.base.modules.tour_dialogue import resolve_turn, local_answer
from server.base.modules.tour_visuals import build_visual_context, safe_image
from server.base.modules.route_presentation import route_overview
from server.base.modules.adaptive_itinerary import repair_route
from server.base.modules.tour_support import scenic_fact_evidence
from test_preference_planner import SPOTS


class WebExperienceTests(unittest.TestCase):
    def setUp(self):
        self.spot = next(s for s in SPOTS if s['spot_name'] == '长廊')

    def test_broad_history_is_substantial_but_specific_fact_is_direct(self):
        broad, refs = local_answer(resolve_turn('这里有什么历史故事？', self.spot), self.spot)
        direct, _ = local_answer(resolve_turn('长廊有多长？', self.spot), self.spot)
        self.assertGreater(len(broad), 200)
        self.assertLessEqual(len(broad), 530)
        self.assertIn('\n\n', broad)
        self.assertIn('728', direct)
        self.assertLess(len(direct), len(broad))
        self.assertTrue(any('gallery_detail' in s['url'] for s in refs))

    def test_updated_database_history_is_used_in_local_preview(self):
        edited = dict(self.spot, history_detail='这是一段管理员正在预览的历史说明。')
        answer, _ = local_answer(resolve_turn('介绍历史', edited), edited)
        self.assertIn('管理员正在预览', answer)

    def test_deep_highlights_have_context_even_without_remote_model(self):
        turn=resolve_turn('请介绍景点特色',self.spot);turn.detailed=True
        answer,_=local_answer(turn,self.spot)
        self.assertGreater(len(answer),250)
        self.assertIn('\n\n',answer)

    def test_verifier_can_quote_exact_database_facts_without_private_fields(self):
        spot=dict(self.spot,history_detail='管理员维护的历史详情。',description='景点简介。',secret='private')
        records=scenic_fact_evidence(spot,['history'])
        self.assertTrue(any(r['excerpt']=='管理员维护的历史详情。' for r in records))
        self.assertTrue(all(r['retrieval_method']=='database-field-snapshot' for r in records))
        self.assertNotIn('private',str(records))
        self.assertEqual(scenic_fact_evidence(spot,['facilities']),[])

    def test_brief_request_remains_brief(self):
        answer, _ = local_answer(resolve_turn('一句话介绍长廊', self.spot), self.spot)
        self.assertLessEqual(len(answer), 160)

    def test_timeline_follows_answer_dates_not_model_invented_events(self):
        context = build_visual_context(self.spot, ['history'], '长廊始建于1750年。')
        self.assertEqual([p['year'] for p in context['timeline']], [1750])
        context = build_visual_context(self.spot, ['history'], '1999年发生一件未知的事情。')
        self.assertEqual(context['timeline'], [])

    def test_english_visuals_are_authored_in_english(self):
        context = build_visual_context(self.spot, ['history'], 'Built in 1750.', 'en')
        self.assertIn('Long Corridor', context['images'][0]['label'])
        self.assertIn('first built', context['timeline'][0]['text'])

    def test_namesakes_and_practical_questions_do_not_get_unrelated_visuals(self):
        self.assertIsNone(build_visual_context(dict(self.spot, city='成都'), ['history'], '1750'))
        self.assertIsNone(build_visual_context(self.spot, ['facilities'], '厕所位置未核实'))

    def test_only_reviewed_hosts_and_local_assets_are_accepted(self):
        for path in ['javascript:alert(1)', '//evil.test/a.jpg', '../secret', 'https://evil.test/a.jpg']:
            self.assertEqual(safe_image(path), '')
        self.assertEqual(safe_image('tour_files/photo.png'), '/api/v1/files/tour_files/photo.png')
        self.assertEqual(safe_image('http://localhost:8000/api/v1/files/tour_files/photo.png'), '/api/v1/files/tour_files/photo.png')

    def test_leg_totals_match_existing_walking_network_and_display_order(self):
        route = SPOTS[:3]
        result = route_overview(route)
        self.assertEqual([s['spot_id'] for s in result['stops']], [s['spot_id'] for s in route])
        self.assertEqual(result['walking_meters'], sum(x['meters'] for x in result['legs']))
        self.assertEqual(result['total_minutes'], result['visit_minutes'] + result['walking_minutes'] + result['rest_minutes'])
        self.assertTrue(all(x['basis'] == 'osm_pedestrian_network' and len(x['geometry']) >= 2 for x in result['legs']))
        relaxed = route_overview(route, 'relaxed')
        self.assertGreaterEqual(relaxed['walking_minutes'], result['walking_minutes'])

    def test_unknown_coordinates_do_not_become_zero_distance(self):
        missing = dict(spot_id=500, spot_name='未定位点', latitude=0, longitude=0)
        result = route_overview([self.spot, missing])
        self.assertFalse(result['complete'])
        self.assertIsNone(result['walking_meters'])
        self.assertIsNone(result['total_minutes'])

    def test_repair_contains_both_routes_and_keeps_completed_prefix(self):
        result = repair_route(SPOTS[:5], 1, SPOTS, 90, excluded=[SPOTS[2]['spot_id']])
        self.assertEqual(result['completed_ids'], [SPOTS[0]['spot_id']])
        self.assertEqual(result['original_route']['stops'][0]['spot_id'], SPOTS[1]['spot_id'])
        self.assertNotIn(SPOTS[2]['spot_id'], [s['spot_id'] for s in result['proposed_route']['stops']])
        self.assertEqual(result['original_route']['stops'][1]['spot_id'], SPOTS[2]['spot_id'])


if __name__ == '__main__':
    unittest.main()
