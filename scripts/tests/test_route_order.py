"""Preserve every stop and check exact results against exhaustive permutations."""
import copy
import itertools
import unittest
from unittest.mock import patch, MagicMock

from server.base.modules.route_order import optimize_order
from server.base.modules.route_presentation import route_overview
from test_preference_planner import SPOTS


class RouteOrderTests(unittest.TestCase):
    def test_exact_matches_exhaustive_search_with_each_endpoint_constraint_and_gates(self):
        spots = [SPOTS[i] for i in [0, 10, 4, 7, 3]]
        for fixed_start, fixed_end in itertools.product([False, True], repeat=2):
            with self.subTest(start=fixed_start, end=fixed_end):
                options = dict(pace='relaxed', start_area='east', end_area='south', reserve=10)
                result = optimize_order(spots, fixed_start=fixed_start, fixed_end=fixed_end, **options)
                candidates = []
                for order in itertools.permutations(spots):
                    if fixed_start and order[0] != spots[0] or fixed_end and order[-1] != spots[-1]:
                        continue
                    overview = route_overview(order, **options)
                    if overview['complete']:
                        candidates.append((overview['walking_meters'], overview['walking_minutes']))
                proposed = result['proposed_route']
                self.assertEqual((proposed['walking_meters'], proposed['walking_minutes']), min(candidates))
                self.assertTrue(result['optimal'])
                self.assertEqual(set(result['spot_ids']), {s['spot_id'] for s in spots})
                self.assertEqual(proposed['reserve_minutes'], 10)
                self.assertIsNotNone(proposed['entry_leg'])
                self.assertIsNotNone(proposed['exit_leg'])

    def test_all_sixteen_are_kept_without_shortening_visits_and_can_be_optimized_again(self):
        original = copy.deepcopy(SPOTS)
        result = optimize_order(SPOTS)
        self.assertEqual(SPOTS, original)
        self.assertEqual(len(result['spot_ids']), 16)
        self.assertEqual(result['spot_ids'][0], SPOTS[0]['spot_id'])
        self.assertEqual(result['proposed_route']['visit_minutes'], result['original_route']['visit_minutes'])
        self.assertGreater(result['saved_meters'], 5000)
        self.assertGreater(result['saved_minutes'], 0)
        self.assertEqual(result['saved_meters'], result['original_route']['walking_meters'] - result['proposed_route']['walking_meters'])
        by_id = {s['spot_id']: s for s in SPOTS}
        again = optimize_order([by_id[i] for i in result['spot_ids']])
        self.assertTrue(again['unchanged'])
        self.assertEqual(again['spot_ids'], result['spot_ids'])
        self.assertTrue(all(leg['basis'] == 'osm_pedestrian_network' and len(leg['geometry']) > 2 for leg in result['proposed_route']['legs']))

    def test_both_locked_endpoints_and_two_stop_selection(self):
        for spots in [SPOTS[:2], SPOTS]:
            result = optimize_order(spots, fixed_start=True, fixed_end=True)
            self.assertEqual(result['spot_ids'][0], spots[0]['spot_id'])
            self.assertEqual(result['spot_ids'][-1], spots[-1]['spot_id'])
            self.assertLessEqual(result['proposed_route']['total_minutes'], result['original_route']['total_minutes'])

    def test_bounded_large_selection_keeps_stops_and_never_claims_exact_optimality(self):
        spots = [dict(SPOTS[(i * 7) % 16], spot_id=100+i) for i in range(20)]
        result = optimize_order(spots, fixed_start=False, fixed_end=False)
        self.assertFalse(result['optimal'])
        self.assertEqual(result['method'], 'multistart_2opt')
        self.assertEqual(set(result['spot_ids']), {s['spot_id'] for s in spots})
        self.assertLessEqual(result['proposed_route']['walking_meters'], result['original_route']['walking_meters'])
        self.assertLessEqual(result['proposed_route']['total_minutes'], result['original_route']['total_minutes'])

    def test_invalid_selection_and_missing_paths_fail_without_fabricated_distances(self):
        for spots in [[], SPOTS[:1], [SPOTS[0], SPOTS[0]], SPOTS + SPOTS[:5],
                      [SPOTS[0], dict(SPOTS[1], spot_name='未知景点', latitude=0)]]:
            with self.subTest(spots=len(spots)), self.assertRaises(ValueError):
                optimize_order(spots)
        with patch('server.base.modules.route_order.network_version', side_effect=['before', 'after']):
            with self.assertRaisesRegex(ValueError, '路网已变化'):
                optimize_order(SPOTS[:3])


class RouteOrderApiTests(unittest.TestCase):
    def test_public_preview_is_read_only_validates_ids_and_preserves_every_stop(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from server.base.routers import tour_experience as api
        from server.base.models.tour_models import ScenicSpotInfo
        records = {s['spot_id']: ScenicSpotInfo(**s) for s in SPOTS}
        db = MagicMock()
        db.get.side_effect = lambda model, sid: records.get(sid)
        context = MagicMock()
        context.__enter__.return_value = db
        app = FastAPI()
        app.include_router(api.router)
        with patch.object(api, 'Session', return_value=context), TestClient(app) as client:
            body = dict(spot_ids=list(records), fixed_start=True, fixed_end=True)
            response = client.post('/tour-experience/optimize-order', json=body)
            self.assertEqual(response.status_code, 200, response.text)
            data = response.json()['data']
            self.assertEqual(data['input_spot_ids'], list(records))
            self.assertEqual(set(data['spot_ids']), set(records))
            self.assertEqual(data['spot_ids'][-1], list(records)[-1])
            for ids in [[1], [1, 1], [1, 999], list(range(21))]:
                self.assertEqual(client.post('/tour-experience/optimize-order', json={'spot_ids':ids}).status_code, 422)
            db.commit.assert_not_called()
            db.add.assert_not_called()


if __name__ == '__main__':
    unittest.main()
