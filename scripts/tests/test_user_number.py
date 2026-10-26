"""验证展示用户编号：年月 + 4 位注册顺序、每月重置、历史账号补号。"""
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy.exc import IntegrityError
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine, select

from server.base.models.user_model import UserInfo
from server.base.modules.user_number import assign_user_no, backfill_user_numbers, month_prefix

CST = timezone(timedelta(hours=8))


class UserNumberTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
        SQLModel.metadata.create_all(self.engine)

    def tearDown(self):
        self.engine.dispose()

    def add_user(self, username, now, create_time=None):
        with Session(self.engine) as session:
            user = UserInfo(username=username, hashed_password='test',
                            create_time=create_time or datetime(2026, 10, 22),
                            delete=False, user_no=assign_user_no(session, now=now))
            session.add(user)
            session.commit()
            return user.user_no

    def test_month_prefix_uses_beijing_time(self):
        self.assertEqual(month_prefix(datetime(2026, 10, 22, 0, 30, tzinfo=CST)), '202610')
        # UTC 时间先换算到北京时间，跨月时归属下一个月。
        self.assertEqual(month_prefix(datetime(2026, 10, 31, 17, 0, tzinfo=timezone.utc)), '202611')

    def test_sequence_increments_and_resets_each_month(self):
        self.assertEqual(self.add_user('first', datetime(2026, 10, 22, tzinfo=CST)), '2026100001')
        self.assertEqual(self.add_user('second', datetime(2026, 10, 23, tzinfo=CST)), '2026100002')
        # 下个月重新从 0001 开始。
        self.assertEqual(self.add_user('november', datetime(2026, 11, 1, tzinfo=CST)), '2026110001')
        # 同一个月继续递增。
        self.assertEqual(self.add_user('november-2', datetime(2026, 11, 2, tzinfo=CST)), '2026110002')

    def test_backfill_numbers_legacy_accounts_in_registration_order(self):
        with Session(self.engine) as session:
            session.add(UserInfo(username='old-b', hashed_password='test',
                                 create_time=datetime(2026, 7, 31, 12, 0), delete=False))
            session.add(UserInfo(username='old-a', hashed_password='test',
                                 create_time=datetime(2026, 7, 31, 8, 0), delete=False))
            session.commit()

        count = backfill_user_numbers(self.engine, now=datetime(2026, 10, 22, tzinfo=CST))
        self.assertEqual(count, 2)
        with Session(self.engine) as session:
            users = session.exec(select(UserInfo).order_by(UserInfo.create_time)).all()
            self.assertEqual([user.user_no for user in users], ['2026100001', '2026100002'])
        # 重复执行不会重复编号。
        self.assertEqual(backfill_user_numbers(self.engine, now=datetime(2026, 10, 22, tzinfo=CST)), 0)
        with Session(self.engine) as session:
            self.assertEqual(assign_user_no(session, now=datetime(2026, 10, 22, tzinfo=CST)), '2026100003')

    def test_user_no_is_unique(self):
        first = self.add_user('first', datetime(2026, 10, 22, tzinfo=CST))
        with Session(self.engine) as session:
            session.add(UserInfo(username='duplicate', hashed_password='test',
                                 create_time=datetime(2026, 10, 22), delete=False, user_no=first))
            with self.assertRaises(IntegrityError):
                session.commit()


if __name__ == '__main__':
    unittest.main()
