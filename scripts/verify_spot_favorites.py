"""Verify real PostgreSQL persistence and account isolation, restoring original state."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from sqlmodel import Session, select
from server.base.base_server import app
from server.base.database.init_db import DB_ENGINE
from server.base.models.spot_favorite import SpotFavorite
from server.base.models.tour_models import ScenicSpotInfo
from server.base.models.user_model import UserInfo
from server.base.routers.users import get_current_user_info

with Session(DB_ENGINE) as session:
    users = session.exec(select(UserInfo).where(UserInfo.delete == False).limit(2)).all()
    spot = session.exec(select(ScenicSpotInfo).where(ScenicSpotInfo.delete == False)).first()
    assert len(users) == 2 and spot, "Need existing users and a real spot"
    first, second, sid = users[0].user_id, users[1].user_id, spot.spot_id

SpotFavorite.__table__.create(DB_ENGINE, checkfirst=True)
with Session(DB_ENGINE) as session:
    original = session.get(SpotFavorite, (first, sid))
    had_original = original is not None
    original_time = original.created_at if original else None

try:
    client = TestClient(app)
    assert client.get('/spot-favorites').status_code == 401
    app.dependency_overrides[get_current_user_info] = lambda: first
    assert client.delete(f'/spot-favorites/{sid}').json()['success']
    assert client.put(f'/spot-favorites/{sid}').json()['data']['favorited']
    assert client.put(f'/spot-favorites/{sid}').json()['success']
    with Session(DB_ENGINE) as session:
        assert len(session.exec(select(SpotFavorite).where(SpotFavorite.user_id == first, SpotFavorite.spot_id == sid)).all()) == 1
    assert sid in [x['spot_id'] for x in client.get('/spot-favorites').json()['data']['spot_list']]
    app.dependency_overrides[get_current_user_info] = lambda: second
    with Session(DB_ENGINE) as session:
        expected = set(session.exec(select(SpotFavorite.spot_id).join(ScenicSpotInfo).where(SpotFavorite.user_id == second, ScenicSpotInfo.delete == False)).all())
        actual = {x['spot_id'] for x in client.get('/spot-favorites').json()['data']['spot_list']}
        assert actual == expected
        assert session.get(SpotFavorite, (first, sid)) is not None
    app.dependency_overrides[get_current_user_info] = lambda: first
    assert client.delete(f'/spot-favorites/{sid}').json()['data']['favorited'] is False
    print('PASS: authentication, real DB persistence, duplicate prevention, account filtering, deletion')
finally:
    app.dependency_overrides.clear()
    with Session(DB_ENGINE) as session:
        row = session.get(SpotFavorite, (first, sid))
        if row:
            session.delete(row)
            session.commit()
        if had_original:
            session.add(SpotFavorite(user_id=first, spot_id=sid, created_at=original_time))
            session.commit()
