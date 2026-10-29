"""Validate account separation at HTTP login and saved-session boundaries."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from fastapi import HTTPException
from server.base.routers import users


def complete(coroutine):
    # These handlers do not suspend; avoid OS event-loop sockets in unit tests.
    try:
        coroutine.send(None)
    except StopIteration as result:
        return result.value
    raise AssertionError('Handler unexpectedly suspended')


class LoginClientSeparationTest(unittest.TestCase):
    def test_login_account_boundaries(self):
        with patch.dict('os.environ', {'ADMIN_USERNAME': 'admin'}), patch.object(
            users.WEB_CONFIGS, 'TOKEN_JWT_SECURITY_KEY', 'isolated-test-signing-key-at-least-32-bytes'
        ), patch.object(users, 'authenticate_user') as authenticate:
            for username, client_type, expected in [
                ('admin', 'app', 403), ('小智', 'app', 200),
                ('admin', 'admin', 200), ('小智', 'admin', 403),
            ]:
                authenticate.return_value = SimpleNamespace(user_id=7, username=username, ip_address=None)
                form = SimpleNamespace(username=username, password='test-password')
                if expected == 403:
                    with self.assertRaises(HTTPException) as raised:
                        complete(users.login(form, client_type))
                    self.assertEqual(raised.exception.status_code, 403)
                else:
                    token = complete(users.login(form, client_type))
                    self.assertTrue(token.access_token)

    def test_app_cannot_restore_administrator_session(self):
        with patch.dict('os.environ', {'ADMIN_USERNAME': 'admin'}), patch.object(
            users, 'get_db_user_info', return_value=SimpleNamespace(username='admin', delete=False)
        ):
            with self.assertRaises(HTTPException) as raised:
                complete(users.get_streaming_room_api(7, 'app'))
            self.assertEqual(raised.exception.status_code, 403)


if __name__ == '__main__':
    unittest.main()
