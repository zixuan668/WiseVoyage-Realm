from fastapi.testclient import TestClient
from server.scenic_preview import app
from server.base.routers.tour_experience import *
c=TestClient(app)
c.get('/tour-experience/scenic-selection')
catalog=c.get('/tour-experience/scenic-catalog').json()
ids=[s['id'] for s in catalog[:3]]
owner=c.cookies.get('scenic_draft')
try:
 for sid in ids:assert c.put('/tour-experience/scenic-selection',params={'spot_id':sid}).status_code==200
 r=c.put('/tour-experience/scenic-settings',json={'spot_ids':ids[::-1],'elderly':True})
 assert r.status_code==200 and r.json()['avoid_steps']
 assert [s['id'] for s in c.get('/tour-experience/scenic-selection').json()]==ids[::-1]
 bad=c.put('/tour-experience/scenic-settings',json={'spot_ids':ids[:1]})
 assert bad.status_code==409
 route=c.post('/tour-experience/route-preview',json={'spot_ids':ids[::-1],'avoid_steps':True,'pace':'relaxed'}).json()
 assert route['success'] and route['data']['avoid_steps']
 assert [s['spot_id'] for s in route['data']['stops']]==ids[::-1]
 assert c.delete('/tour-experience/scenic-selection/'+str(ids[0])).status_code==200
 assert len(c.get('/tour-experience/scenic-selection').json())==2
 print('PASS order persistence, accessibility, route recomputation, deletion, stale-order rejection')
finally:
 with Session(DB_ENGINE) as db:
  for row in db.exec(select(ScenicDraftStop).where(ScenicDraftStop.owner==owner)).all():db.delete(row)
  row=db.get(ScenicDraftSettings,owner)
  if row:db.delete(row)
  db.commit()
