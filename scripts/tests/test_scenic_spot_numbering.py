"""Exercise catalog numbering through real queries without changing route IDs."""
import unittest
from unittest.mock import patch

from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine

# Register the legacy tables referenced by the shared SQLModel metadata.
from server.base.database import scenic_spot_db
from server.base.models.tour_models import ScenicSpotInfo, SpotPageItem, TourRoute, TourRouteSpot
from server.base.modules.route_city import summer_palace_spot_numbers


class ScenicSpotNumberingTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://', poolclass=StaticPool)
        SQLModel.metadata.create_all(self.engine)
        self.db_patch = patch.object(scenic_spot_db, 'DB_ENGINE', self.engine)
        self.db_patch.start()
        with Session(self.engine) as db:
            for number, name in enumerate(('故宫博物院', '长城(八达岭)'), 1):
                db.add(ScenicSpotInfo(spot_id=number, spot_name=name, user_id=1, delete=True))
            for name, number in summer_palace_spot_numbers().items():
                db.add(ScenicSpotInfo(
                    spot_id=number + 2, spot_name=name, user_id=1,
                    category='natural' if name == '昆明湖' else 'historical',
                ))
            db.add(ScenicSpotInfo(spot_id=30, spot_name='其他用户景点', user_id=2))
            db.add(TourRoute(route_id=1, name='现有路线', user_id=1))
            db.add(TourRouteSpot(route_id=1, spot_id=5, spot_order=0))
            db.commit()

    def tearDown(self):
        self.db_patch.stop()
        self.engine.dispose()

    async def test_pages_serialize_contiguous_numbers_and_keep_route_ids(self):
        first, total = await scenic_spot_db.get_db_scenic_spot_info(1, 1, 10)
        second, second_total = await scenic_spot_db.get_db_scenic_spot_info(1, 2, 10)
        self.assertEqual((total, second_total), (16, 16))
        payload = SpotPageItem(spot_list=first + second).model_dump()
        self.assertEqual([s['spot_number'] for s in payload['spot_list']], list(range(1, 17)))
        self.assertEqual([s['spot_id'] for s in payload['spot_list']], list(range(3, 19)))
        with Session(self.engine) as db:
            self.assertEqual(db.get(TourRouteSpot, 1).spot_id, 5)
            self.assertEqual(db.get(ScenicSpotInfo, 5).spot_name, '佛香阁')

    async def test_search_and_category_keep_numbers_and_count_only_matches(self):
        spots, total = await scenic_spot_db.get_db_scenic_spot_info(
            1, 1, 10, spot_name='昆明', category='natural',
        )
        self.assertEqual(total, 1)
        self.assertEqual([(s.spot_number, s.spot_id) for s in spots], [(4, 6)])
        spots, total = await scenic_spot_db.get_db_scenic_spot_info(
            1, 1, 10, spot_name='昆明', category='historical',
        )
        self.assertEqual((spots, total), ([], 0))

    async def test_exclusions_and_deleted_records_do_not_leak_into_results(self):
        spots, total = await scenic_spot_db.get_db_scenic_spot_info(
            1, category='historical', exclude_list=[3, 4],
        )
        self.assertEqual(total, 13)
        self.assertTrue(all(s.spot_number and s.spot_id not in (1, 2, 3, 4, 30) for s in spots))
        spots, total = await scenic_spot_db.get_db_scenic_spot_info(1, spot_id=1)
        self.assertEqual((spots, total), ([], 0))


if __name__ == '__main__':
    unittest.main()
