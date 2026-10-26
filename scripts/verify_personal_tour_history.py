"""Regression checks: real DB selections, no test session writes."""
import asyncio, json, os, sys, urllib.request, urllib.error
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
for line in Path('.env').read_text(encoding='utf-8-sig').splitlines():
    if '=' in line and not line.lstrip().startswith('#'):
        key,value=line.split('=',1);os.environ.setdefault(key.strip(),value.strip().strip(chr(34)).strip(chr(39)))
from server.base.routers import tour_chat, users
from server.web_configs import WEB_CONFIGS
from sqlmodel import Session, select
from server.base.database.init_db import DB_ENGINE
from server.base.models.tour_models import TourSessionInfo
base='http://127.0.0.1:8000/api/v1/tour-session/'
for endpoint in ('my-history','my-history/1/messages'):
    try: urllib.request.urlopen(base+endpoint,timeout=15);raise AssertionError('authentication required')
    except urllib.error.HTTPError as exc: assert exc.code==401,exc.code
with Session(DB_ENGINE) as db:
    actual=db.exec(select(TourSessionInfo).where(TourSessionInfo.user_id != None)).first()
assert actual
uid=actual.user_id
token=users.jwt.encode({'user_id':uid},WEB_CONFIGS.TOKEN_JWT_SECURITY_KEY,algorithm=WEB_CONFIGS.TOKEN_JWT_ALGORITHM)
owned=SimpleNamespace(user_id=uid,visitor_preferences=json.dumps({'owner_user_id':uid}))
assert tour_chat._history_owner(owned,uid)
assert not tour_chat._history_owner(owned,uid+1)
assert not tour_chat._history_owner(SimpleNamespace(user_id=uid,visitor_preferences='{}'),uid)
async def verify_create():
    captured=[]
    async def capture(**kwargs):captured.append(kwargs);return SimpleNamespace(session_id=0)
    with patch.object(tour_chat,'create_tour_session',capture):
        await tour_chat.visitor_create_session(name='ownership regression',guide_id=1,visitor_preferences='history',spot_ids='[44]',route_id=0,authorization='Bearer '+token)
        await tour_chat.visitor_create_session(name='ownership regression',guide_id=1,visitor_preferences='history',spot_ids='[44]',route_id=0,authorization=None)
    assert captured[0]['user_id']==uid
    assert json.loads(captured[0]['visitor_preferences'])['owner_user_id']==uid
    assert captured[1]['user_id'] is None
asyncio.run(verify_create())
request=urllib.request.Request(base+'my-history',headers={'Authorization':'Bearer '+token})
result=json.load(urllib.request.urlopen(request,timeout=20));assert result['success']
with Session(DB_ENGINE) as db:
    for item in result['data']['session_list']:
        actual=db.get(TourSessionInfo,item['session_id']);assert tour_chat._history_owner(actual,uid)
print('PASS: authentication, own-user history, cross-user/legacy exclusion, authenticated and anonymous creation ownership; no test records saved')
