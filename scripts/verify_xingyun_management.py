"""隔离 SQL 数据库验证多数字人 CRUD、权限、公开列表及云端凭据路由；不调用星云计费接口。"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import os
from unittest.mock import patch
import httpx
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine, select
from sqlalchemy.pool import StaticPool
from server.base.base_server import app
from server.web_configs import WEB_CONFIGS
from server.base.database import init_db, digital_guide_db, tour_session_db
from server.base.modules import xingyun_access
from server.base.routers import digital_guide, xingyun
from server.base.routers.users import get_current_user_info
from server.base.models.user_model import UserInfo
from server.base.models.tour_models import DigitalGuideInfo, TourRoute, ScenicSpotInfo, TourSessionInfo
from server.base.models.xingyun import XingyunGuideBinding

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
SQLModel.metadata.create_all(engine)
modules = [init_db, digital_guide_db, tour_session_db, xingyun_access, xingyun, digital_guide]
patchers = [patch.object(module, "DB_ENGINE", engine) for module in modules]
for p in patchers:
    p.start()
old_key = WEB_CONFIGS.TOKEN_JWT_SECURITY_KEY
WEB_CONFIGS.TOKEN_JWT_SECURITY_KEY = "isolated-xingyun-test-key-only-32-bytes-plus"
calls = []

class CloudClient:
    def __init__(self, **kwargs):
        pass
    async def __aenter__(self):
        return self
    async def __aexit__(self, *args):
        pass
    async def request(self, method, url, **kwargs):
        calls.append((method, kwargs["headers"], kwargs["json"]))
        app_id = kwargs["headers"]["X-APP-ID"]
        if method == "POST":
            return httpx.Response(200, json={"data": {"resource_pack": {"fixture": True}, "session_id": "session-" + app_id, "request_id": "request-" + app_id}})
        return httpx.Response(200, json={"error_code": 0})

try:
    with Session(engine) as db:
        db.add(UserInfo(user_id=1, username=os.getenv("ADMIN_USERNAME", "admin"), hashed_password="unused-test-fixture"))
        db.add(UserInfo(user_id=2, username="visitor-fixture", hashed_password="unused-test-fixture"))
        route = TourRoute(name="test-route", user_id=1)
        spot = ScenicSpotInfo(spot_name="test-spot", city="北京", location="北京市海淀区颐和园", user_id=1)
        db.add(route); db.add(spot); db.commit(); db.refresh(route); db.refresh(spot)
        route_id, spot_id = route.route_id, spot.spot_id
    client = TestClient(app)
    assert client.get("/digital-guide/list").status_code == 401
    assert client.post("/xingyun/guides", json={"name": "x", "app_id": "x", "app_secret": "x"}).status_code == 401
    app.dependency_overrides[get_current_user_info] = lambda: 2
    assert client.get("/digital-guide/list").status_code == 403
    assert client.put("/xingyun/admin/1", json={"app_id": "x", "app_secret": "x"}).status_code == 403
    app.dependency_overrides[get_current_user_info] = lambda: 1
    invalid = client.post("/xingyun/guides", json={"name": "no-cover", "app_id": "x", "app_secret": "private-invalid-secret"})
    assert invalid.status_code == 400 and "private-invalid-secret" not in invalid.text
    created = client.post("/xingyun/guides", json={"name": "direct-cloud-guide", "app_id": "direct-app", "app_secret": "direct-secret", "poster_image": "/fixture/cover.png", "avatar": "/fixture/head.png"})
    assert created.status_code == 200, created.text
    with Session(engine) as db:
        direct = db.get(DigitalGuideInfo, created.json()["guide_id"])
        assert direct.render_mode == "xingyun" and not direct.is_enabled
        assert direct.avatar == "/fixture/head.png" and direct.poster_image == "/fixture/cover.png"
        saved = db.get(XingyunGuideBinding, direct.guide_id)
        assert saved.app_id == "direct-app" and xingyun_access.decrypt_secret(saved.secret_encrypted) == "direct-secret"
    assert "direct-secret" not in created.text
    ids, tours, tokens = [], [], []
    for suffix in ("a", "b"):
        result = client.post("/digital-guide/create", json={
            "name": "guide-" + suffix, "character": "test guide",
            "poster_image": "/fixture/full.png", "avatar": "/fixture/avatar.png", "is_enabled": False,
        }).json()
        assert result["success"], result
        with Session(engine) as db:
            guide_id = db.exec(select(DigitalGuideInfo).where(DigitalGuideInfo.name == "guide-" + suffix)).one().guide_id
        ids.append(guide_id)
        binding = {"app_id": "app-" + suffix, "app_secret": "secret-" + suffix, "voice_label": "voice-" + suffix}
        assert client.put("/xingyun/admin/" + str(guide_id), json=binding).status_code == 200
        read = client.get("/xingyun/admin/" + str(guide_id)).json()
        assert read["secret_configured"] and "app_secret" not in read and "secret_encrypted" not in read
        assert client.put("/digital-guide/publication/" + str(guide_id), json={"is_enabled": True}).json()["success"]
        made = client.post("/tour-session/visitor-create", params={
            "guide_id": guide_id, "spot_ids": "[" + str(spot_id) + "]", "route_id": route_id, "visitor_preferences": "历史",
        }).json()
        assert made["success"], made
        tours.append(made["data"]["session_id"]); tokens.append(made["data"]["avatar_access_token"])
        with Session(engine) as db:
            assert db.get(TourSessionInfo, tours[-1]).guide_id == guide_id
            saved = db.get(XingyunGuideBinding, guide_id)
            assert saved.secret_encrypted != binding["app_secret"]
            assert xingyun_access.decrypt_secret(saved.secret_encrypted) == binding["app_secret"]
    public = client.get("/tour-session/guides").json()["data"]["guide_list"]
    assert {g["guide_id"] for g in public} == set(ids)
    assert "secret-" not in str(public) and "app_id" not in str(public)
    assert client.get("/xingyun/config/" + str(ids[0])).json()["configured"]
    # The App connects through its bundled SDK; the retired browser tour is absent.
    assert client.get(f"/xingyun/webview/{tours[0]}").status_code == 404
    with patch.object(xingyun.httpx, "AsyncClient", CloudClient):
        # 无凭证及串用人物均在访问云端前被拒绝。
        assert client.post(f"/xingyun/session/{ids[0]}?tour_id={tours[0]}", json={}).status_code == 401
        assert client.post(f"/xingyun/session/{ids[1]}?tour_id={tours[0]}", json={}, headers={"X-Tour-Access": tokens[0]}).status_code == 403
        assert not calls
        for gid, tid, token in zip(ids, tours, tokens):
            response = client.post(f"/xingyun/session/{gid}?tour_id={tid}", json={"config": {}}, headers={"X-Tour-Access": token})
            assert response.status_code == 200, response.text
        assert [c[1]["X-APP-ID"] for c in calls] == ["app-a", "app-b"]
        with Session(engine) as db:
            records = db.exec(select(xingyun.XingyunSession)).all()
            assert len(records) == 2 and all(r.status == "connected" for r in records)
        # 更换应用后，既有会话释放仍使用原始凭据；更换 ID 不能沿用旧密钥。
        assert client.put(f"/xingyun/admin/{ids[0]}", json={"app_id": "new-app"}).status_code == 400
        assert client.put(f"/xingyun/admin/{ids[0]}", json={"app_id": "new-app", "app_secret": "new-secret"}).status_code == 200
        assert client.put(f"/digital-guide/publication/{ids[0]}", json={"is_enabled": False}).json()["success"]
        close = client.request(
            "DELETE", f"/xingyun/session/{ids[0]}?tour_id={tours[0]}", json={"session_id": "session-app-a", "request_id": "forged-request"},
            headers={"X-Tour-Access": tokens[0]})
        assert close.status_code == 200, close.text
        assert calls[-1][1]["X-APP-ID"] == "app-a" and calls[-1][2]["request_id"] == "request-app-a"
        assert client.post(f"/xingyun/session/{ids[0]}?tour_id={tours[0]}", json={}, headers={"X-Tour-Access": tokens[0]}).status_code == 409
    public = client.get("/tour-session/guides").json()["data"]["guide_list"]
    assert [g["guide_id"] for g in public] == [ids[1]]
    assert client.delete(f"/digital-guide/delete/{ids[1]}").json()["success"]
    assert client.get("/tour-session/guides").json()["data"]["guide_list"] == []
    # 历史会话保留原人物身份；下架/删除后的新问题明确失败，不静默换人。
    for guide_id, tour_id in zip(ids, tours):
        live = client.get(f"/tour-session/live-info/{tour_id}").json()["data"]
        assert live["guide_info"]["guide_id"] == guide_id
        assert live["guide_info"]["is_enabled"] is False
        assert not client.put("/tour-session/chat", json={"sessionId": tour_id, "message": "介绍景点"}).json()["success"]
    print("PASS: administrator authorization, guide CRUD/publication, encrypted persistence, secret redaction, visitor selection, per-guide cloud credentials, mismatched-token rejection, release after rotation/unpublication, deletion.")
finally:
    app.dependency_overrides.clear()
    WEB_CONFIGS.TOKEN_JWT_SECURITY_KEY = old_key
    for p in reversed(patchers):
        p.stop()
    engine.dispose()
