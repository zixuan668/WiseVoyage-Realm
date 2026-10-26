"""使用隔离 SQLite 库验证昵称注册与登录，不改动真实账号。"""
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine, select
from server.base.base_server import app
from server.base.database import init_db, user_db
from server.base.models.user_model import UserInfo, EmailVerification
from server.base.modules.email_registration import code_digest


class NicknameRegistrationTest(unittest.TestCase):
    def test_registration_login_and_duplicate_nickname(self):
        engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
        SQLModel.metadata.create_all(engine)
        client = TestClient(app)
        def seed(email):
            with Session(engine) as db:
                db.add(EmailVerification(email=email, code_hash=code_digest(email, '123456'), expires_at=int(time.time())+600, sent_at=int(time.time()), sender_ip='test'))
                db.commit()
        with patch.object(init_db, 'DB_ENGINE', engine), patch.object(user_db, 'DB_ENGINE', engine):
            seed('nickname-test@example.com')
            response = client.post('/user/register', json={'email': 'nickname-test@example.com', 'nickname': 'cc123', 'password': 'isolated-test-password', 'code': '123456'})
            self.assertEqual(response.status_code, 200, response.text)
            with Session(engine) as db:
                user = db.exec(select(UserInfo).where(UserInfo.email == 'nickname-test@example.com')).one()
                self.assertEqual(user.username, 'cc123')
                # 新账号获得「年月 + 4 位顺序」的展示编号，第一个账号为 0001。
                self.assertRegex(user.user_no, r'^\d{6}0001$')
                registered_no = user.user_no
            for name in ('cc123', 'nickname-test@example.com'):
                login = client.post('/user/login', data={'username': name, 'password': 'isolated-test-password'})
                self.assertEqual(login.status_code, 200, login.text)
                me = client.get('/user/me', headers={'Authorization': 'Bearer '+login.json()['access_token']})
                self.assertEqual(me.json()['data']['username'], 'cc123')
                self.assertEqual(me.json()['data']['user_no'], registered_no)
            self.assertEqual(client.post('/user/login', data={'username': 'cc123', 'password': 'wrong'}).status_code, 401)
            seed('other-test@example.com')
            duplicate = client.post('/user/register', json={'email': 'other-test@example.com', 'nickname': 'cc123', 'password': 'isolated-test-password', 'code': '123456'})
            self.assertEqual(duplicate.status_code, 409)
        engine.dispose()


if __name__ == '__main__':
    unittest.main()
