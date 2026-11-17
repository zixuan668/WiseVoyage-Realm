from fastapi.testclient import TestClient
from server.scenic_preview import app
from server.base.routers.tour_experience import *
from sqlmodel import Session,select
from server.base.database.tour_session_db import delete_tour_session
import asyncio
c=TestClient(app)
c.get('/tour-experience/scenic-selection')
guides=c.get('/tour-experience/companions').json()
places=c.get('/tour-experience/scenic-catalog').json()
r=c.post('/tour-experience/journeys',json={'mode':'guide','guide_id':guides[0]['guide_id'],'spot_ids':[places[0]['id']]})
print('guide create',r.status_code)
if r.status_code!=200:
 print(str(r.json())[:200])
 raise SystemExit(1)
data=r.json()
try:
 assert data['tour_id'] and data['access_token']
 response=c.get('/avatar/capabilities/'+str(guides[0]['guide_id']))
 print('avatar capability',response.status_code)
 response=c.put('/tour-session/chat',headers={'X-Tour-Access':data['access_token']},json={'sessionId':data['tour_id'],'message':'介绍一下这里','currentSpotId':places[0]['id'],'text_only':True})
 result=response.json()
 print('chat',response.status_code,'success',result.get('success'),'fields',list(result.get('data') or {}))
 assert response.status_code==200 and result.get('success')
finally:
 c.put('/tour-experience/journeys/'+data['id']+'/end')
 asyncio.run(delete_tour_session(data['tour_id']))
 with Session(DB_ENGINE) as db:
  db.delete(db.get(ScenicJourney,data['id']));db.commit()
