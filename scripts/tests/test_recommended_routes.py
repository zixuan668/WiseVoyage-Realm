"""Curated recommendations must stay consistent with their stop order and road data."""
import copy
import json
import unittest
from pathlib import Path

from server.base.modules.recommended_routes import route_profiles, route_editorial
from server.base.modules.route_presentation import route_overview

ROOT = Path(__file__).resolve().parents[2]
LOCATIONS = json.loads((ROOT / 'data/summer_palace_locations.json').read_text(encoding='utf-8'))['spots']


class RecommendedRoutesTest(unittest.TestCase):
    def members(self, profile):
        return [dict(spot_id=i+1, spot_name=row[0], city='北京', visit_duration=20,
                     latitude=LOCATIONS[row[0]]['latitude'], longitude=LOCATIONS[row[0]]['longitude'])
                for i, row in enumerate(profile['stops'])]

    def test_all_eight_routes_are_distinct_complete_and_bilingual(self):
        profiles = route_profiles()
        self.assertEqual(len(profiles), 8)
        self.assertEqual(len({p['name'] for p in profiles}), 8)
        self.assertEqual(len({tuple(s[0] for s in p['stops']) for p in profiles}), 8)
        for profile in profiles:
            with self.subTest(route=profile['name']):
                spots = self.members(profile)
                self.assertGreaterEqual(len(spots), 5)
                overview = route_overview(spots)
                self.assertTrue(overview['complete'])
                self.assertGreater(overview['walking_meters'], 0)
                result = route_editorial(profile['name'], spots, overview)
                self.assertEqual([s['spot_id'] for s in result['itinerary_stops']], [s['spot_id'] for s in spots])
                self.assertEqual(len(result['walking_legs']), len(spots)-1)
                self.assertEqual(sum(l['meters'] for l in result['walking_legs']), overview['walking_meters'])
                self.assertEqual(len(result['editorial']['en']['highlights']), 3)
                self.assertTrue(all(s['focus']['zh'] and s['focus']['en'] for s in result['itinerary_stops']))
                self.assertTrue(all(len(leg['geometry']) > 2 for leg in overview['legs']))

    def test_operator_reorder_never_receives_stale_curated_stories(self):
        profile = route_profiles()[0]
        spots = self.members(profile)
        spots[0], spots[1] = spots[1], spots[0]
        overview = route_overview(spots)
        result = route_editorial(profile['name'], spots, overview)
        self.assertEqual(result['editorial'], {})
        self.assertEqual(result['editorial_sources'], [])
        self.assertEqual(result['itinerary_stops'][0]['spot_name'], spots[0]['spot_name'])

    def test_other_cities_and_custom_names_do_not_inherit_palace_content(self):
        profile = route_profiles()[0]
        spots = self.members(profile)
        overview = route_overview(spots)
        self.assertEqual(route_editorial('Custom route', spots, overview)['editorial'], {})
        foreign = copy.deepcopy(spots)
        for spot in foreign:
            spot['city'] = '上海'
        self.assertEqual(route_editorial(profile['name'], foreign, overview)['editorial'], {})


if __name__ == '__main__':
    unittest.main()
