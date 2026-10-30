import unittest
from unittest.mock import patch
from sqlmodel import SQLModel, Session, create_engine
from server.base.models.user_model import UserInfo
from server.base.models.tour_models import ScenicSpotInfo, TourSessionInfo, TourRoute, TourRouteSpot
from server.base.database import analytics_db


class HotSpotRankingTest(unittest.TestCase):
    def test_saved_app_itinerary_overrides_legacy_route_and_counts_once(self):
        engine = create_engine('sqlite://')
        SQLModel.metadata.create_all(engine)
        with Session(engine) as db:
            db.add_all([ScenicSpotInfo(spot_id=1, spot_name='A'), ScenicSpotInfo(spot_id=2, spot_name='B'),
                        TourRoute(route_id=1, name='Legacy'), TourRouteSpot(route_id=1, spot_id=2),
                        TourSessionInfo(visitor_preferences='{"spot_ids":[1,1]}'),
                        TourSessionInfo(route_id=1, visitor_preferences='{"spot_ids":[1]}'),
                        TourSessionInfo(route_id=1),
                        TourSessionInfo(route_id=1, visitor_preferences='{"spot_ids":[]}'),
                        TourSessionInfo(delete=True, visitor_preferences='{"spot_ids":[1]}')])
            db.commit()
        with patch.object(analytics_db, 'DB_ENGINE', engine):
            coroutine = analytics_db.get_hot_spot_ranking()
            try:
                coroutine.send(None)
            except StopIteration as result:
                counts = {row['spot_name']: row['session_count'] for row in result.value}
            self.assertEqual(counts, {'A': 2, 'B': 1})


if __name__ == '__main__':
    unittest.main()
