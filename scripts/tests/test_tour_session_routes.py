import asyncio
import json
import unittest
from unittest.mock import patch
from sqlmodel import SQLModel, Session, create_engine
from server.base.database import tour_session_db as db
from server.base.models.tour_models import ScenicSpotInfo, TourRoute, TourRouteSpot, TourSessionInfo, TourSessionStatus


class SessionRouteTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://')
        SQLModel.metadata.create_all(self.engine)
        self.engine_patch = patch.object(db, 'DB_ENGINE', self.engine)
        self.engine_patch.start()
        with Session(self.engine) as session:
            session.add_all([ScenicSpotInfo(spot_id=i, spot_name=f'site-{i}') for i in [1,2,3]])
            session.add(TourRoute(route_id=1, name='fixed'))
            session.commit()
            session.add_all([TourRouteSpot(route_id=1, spot_id=2, spot_order=1),
                             TourRouteSpot(route_id=1, spot_id=1, spot_order=2)])
            session.commit()

    def tearDown(self):
        self.engine_patch.stop()
        self.engine.dispose()

    def create(self, ids=None, route_id=None, index=0, raw=None):
        with Session(self.engine) as session:
            status=TourSessionStatus(current_spot_index=index)
            session.add(status)
            session.commit()
            tour=TourSessionInfo(name='route-test',route_id=route_id,status_id=status.status_id,
                visitor_preferences=raw if raw is not None else json.dumps({'spot_ids':ids}) if ids is not None else '{}')
            session.add(tour)
            session.commit()
            return tour.session_id

    def live(self, sid):
        return asyncio.run(db.get_session_live_info(sid))

    def advance(self, sid):
        return asyncio.run(db.next_spot_in_session(sid))

    def test_custom_itinerary_loads_and_advances_in_saved_order(self):
        sid=self.create([3,1,2])
        info=self.live(sid)
        self.assertEqual([s['spot_id'] for s in info['route_spots']],[3,1,2])
        self.assertEqual(info['current_spot_info']['spot_id'],3)
        self.assertEqual(info['next_spot_info']['spot_id'],1)
        self.assertTrue(self.advance(sid))
        self.assertEqual(self.live(sid)['current_spot_info']['spot_id'],1)
        self.assertTrue(self.advance(sid))
        self.assertTrue(self.live(sid)['final_spot'])
        self.assertFalse(self.advance(sid))
        self.assertEqual(self.live(sid)['current_spot_index'],2)

    def test_legacy_fixed_route_respects_spot_order(self):
        info=self.live(self.create(route_id=1))
        self.assertEqual([s['spot_id'] for s in info['route_spots']],[2,1])
        self.assertEqual(info['current_spot_info']['spot_id'],2)

    def test_saved_selection_overrides_fixed_route_without_reordering(self):
        info=self.live(self.create([3,2],route_id=1))
        self.assertEqual([s['spot_id'] for s in info['route_spots']],[3,2])

    def test_empty_missing_deleted_or_malformed_route_is_explicit_error(self):
        with Session(self.engine) as session:
            deleted=session.get(ScenicSpotInfo,3)
            deleted.delete=True
            session.add(deleted)
            session.commit()
        for ids in [[],[99],[1,3],['1']]:
            with self.subTest(ids=ids):
                sid=self.create(ids)
                self.assertTrue(self.live(sid)['route_error'])
                self.assertIsNone(self.live(sid)['current_spot_info'])
                self.assertFalse(self.advance(sid))

    def test_out_of_range_progress_never_advances_or_wraps(self):
        for index in [-1,10]:
            sid=self.create([1,2],index=index)
            self.assertTrue(self.live(sid)['route_error'])
            self.assertFalse(self.advance(sid))

    def test_single_site_is_immediately_final(self):
        sid=self.create([1])
        self.assertTrue(self.live(sid)['final_spot'])
        self.assertIsNone(self.live(sid)['next_spot_info'])
        self.assertFalse(self.advance(sid))


if __name__=='__main__': unittest.main()
