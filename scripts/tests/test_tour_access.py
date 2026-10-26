"""Exercise the public HTTP routes with real JWTs and an isolated SQL database."""
import json
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import jwt
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine

from server.web_configs import WEB_CONFIGS
from server.base.database import init_db, tour_session_db
from server.base.models.user_model import UserInfo
from server.base.models.tour_models import DigitalGuideInfo, ScenicSpotInfo, TourSessionInfo, TourSessionStatus
from server.base.modules import tour_access, xingyun_access
from server.base.routers import tour_chat


class TourAccessTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
        SQLModel.metadata.create_all(self.engine)
        for target, name, value in [
            (tour_access, 'DB_ENGINE', self.engine), (tour_session_db, 'DB_ENGINE', self.engine),
            (init_db, 'DB_ENGINE', self.engine), (xingyun_access, 'DB_ENGINE', self.engine),
            (WEB_CONFIGS, 'TOKEN_JWT_SECURITY_KEY', 'isolated-tour-access-signing-key-32bytes'),
        ]:
            item = patch.object(target, name, value)
            item.start()
            self.addCleanup(item.stop)
        with Session(self.engine) as db:
            db.add_all([UserInfo(user_id=i, username=name, hashed_password='unused')
                        for i, name in [(1, 'owner'), (2, 'other'), (3, 'admin')]])
            db.add(DigitalGuideInfo(guide_id=1, name='audio guide', render_mode='audio'))
            db.add(ScenicSpotInfo(spot_id=1, spot_name='颐和园', city='北京'))
            db.commit()
        app = FastAPI()
        app.include_router(tour_chat.router)
        self.client = TestClient(app)
        self.addCleanup(self.engine.dispose)
        self.addCleanup(self.client.close)
        self.owner = self.login(1)
        self.other = self.login(2)
        created = self.client.post('/tour-session/visitor-create', params={'guide_id': 1, 'spot_ids': '[1]'}, headers=self.owner)
        self.assertEqual(created.status_code, 200, created.text)
        self.sid = created.json()['data']['session_id']
        self.access = {'X-Tour-Access': created.json()['data']['avatar_access_token']}

    def login(self, uid):
        token = jwt.encode({'user_id': uid, 'exp': datetime.now(timezone.utc) + timedelta(minutes=5)},
                           WEB_CONFIGS.TOKEN_JWT_SECURITY_KEY, algorithm='HS256')
        return {'Authorization': 'Bearer ' + token}

    def test_anonymous_and_other_account_cannot_read_end_delete_or_use_alternate_routes(self):
        routes = [('GET', 'live-info'), ('GET', 'detail'), ('PUT', 'end'), ('PUT', 'start'),
                  ('POST', 'next-spot'), ('POST', 'analyze'), ('POST', 'quiz'),
                  ('POST', 'analyze-questions'), ('POST', 'session-report'), ('DELETE', '')]
        for headers in [{}, self.other]:
            for method, action in routes:
                with self.subTest(method=method, action=action, anonymous=not headers):
                    path = f'/tour-session/{action + "/" if action else ""}{self.sid}'
                    self.assertEqual(self.client.request(method, path, headers=headers).status_code, 403 if headers else 401)
        with Session(self.engine) as db:
            tour = db.get(TourSessionInfo, self.sid)
            self.assertFalse(tour.delete)
            self.assertEqual(tour.status.live_status, 1)

    def test_body_and_query_session_ids_are_also_authorized(self):
        for headers in [{}, self.other]:
            requests = [
                ('PUT', '/tour-session/chat', {'json': {'sessionId': self.sid, 'message': 'hello'}}),
                ('POST', '/tour-session/asr', {'json': {'sessionId': self.sid}}),
                ('POST', '/tour-session/check-nearby', {'params': {'session_id': self.sid, 'latitude': 40, 'longitude': 116}}),
                ('POST', '/tour-session/compare-sessions', {'json': [self.sid, self.sid + 1]}),
            ]
            for method, path, kwargs in requests:
                with self.subTest(path=path):
                    self.assertEqual(self.client.request(method, path, headers=headers, **kwargs).status_code, 403 if headers else 401)

    def test_owner_and_scoped_token_can_read_end_and_delete(self):
        for headers in [self.owner, self.access, self.login(3)]:
            result = self.client.get(f'/tour-session/live-info/{self.sid}', headers=headers)
            self.assertEqual(result.status_code, 200, result.text)
            self.assertTrue(result.json()['success'])
        self.assertTrue(self.client.put(f'/tour-session/end/{self.sid}', headers=self.owner).json()['success'])
        self.assertEqual(self.client.get(f'/tour-session/live-info/{self.sid}', headers=self.access).status_code, 200)
        self.assertTrue(self.client.delete(f'/tour-session/{self.sid}', headers=self.owner).json()['success'])
        self.assertEqual(self.client.get(f'/tour-session/live-info/{self.sid}', headers=self.owner).status_code, 404)

    def test_anonymous_tour_token_is_scoped_and_expiring(self):
        created = self.client.post('/tour-session/visitor-create', params={'guide_id': 1, 'spot_ids': '[1]'}).json()['data']
        sid = created['session_id']
        headers = {'X-Tour-Access': created['avatar_access_token']}
        self.assertEqual(self.client.get(f'/tour-session/live-info/{sid}', headers=headers).status_code, 200)
        self.assertEqual(self.client.get(f'/tour-session/live-info/{self.sid}', headers=headers).status_code, 401)
        claims = jwt.decode(headers['X-Tour-Access'], WEB_CONFIGS.TOKEN_JWT_SECURITY_KEY, algorithms=['HS256'])
        claims['exp'] = datetime.now(timezone.utc) - timedelta(seconds=1)
        expired = jwt.encode(claims, WEB_CONFIGS.TOKEN_JWT_SECURITY_KEY, algorithm='HS256')
        for token in [expired, 'tampered']:
            self.assertEqual(self.client.get(f'/tour-session/live-info/{sid}', headers={'X-Tour-Access': token}).status_code, 401)

    def test_session_list_requires_admin(self):
        self.assertEqual(self.client.get('/tour-session/list', headers=self.other).status_code, 403)
        self.assertEqual(self.client.get('/tour-session/list', headers=self.login(3)).status_code, 200)


if __name__ == '__main__':
    unittest.main()
