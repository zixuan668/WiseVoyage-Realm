from fastapi.testclient import TestClient
from server.scenic_preview import app
from sqlmodel import Session,select
from server.base.routers.tour_experience import *
client=TestClient(app)
assert client.get('/tour-experience/scenic-selection').status_code==200
guides=client.get('/tour-experience/companions')
print('guides',guides.status_code, 'available',len(guides.json()) if guides.status_code==200 else 'failed')
places=client.get('/tour-experience/scenic-catalog').json()
jid=None
try:
 r=client.post('/tour-experience/journeys',json={'mode':'walk','spot_ids':[places[0]['id'],places[1]['id']]})
 assert r.status_code==200,r.text
 jid=r.json()['id']
 data=client.get('/tour-experience/journeys/'+jid).json()
 assert len(data['spots'])==2
 other=TestClient(app)
 assert other.get('/tour-experience/journeys/'+jid).status_code==404
 target=data['spots'][0]
 bad=client.post('/tour-experience/journeys/'+jid+'/arrivals',json={'spot_id':target['spot_id'],'latitude':0,'longitude':0,'accuracy':10})
 assert bad.status_code==422
 good={'spot_id':target['spot_id'],'latitude':target['latitude'],'longitude':target['longitude'],'accuracy':10}
 assert client.post('/tour-experience/journeys/'+jid+'/arrivals',json=good).status_code==200
 assert client.post('/tour-experience/journeys/'+jid+'/arrivals',json=good).status_code==200
 assert len(client.get('/tour-experience/journeys/'+jid).json()['arrivals'])==1
 body={'quick':2,'satisfaction':2,'tags':['风景优美'],'recommendation':9}
 assert client.put('/tour-experience/journeys/'+jid+'/review',json=body).status_code==409
 assert client.put('/tour-experience/journeys/'+jid+'/end').status_code==200
 assert client.put('/tour-experience/journeys/'+jid+'/review',json=body).status_code==200
 assert client.get('/tour-experience/journeys/'+jid).json()['review']['recommendation']==9
 print('PASS journey, ownership, distance rejection, idempotent arrival, end and review persistence')
finally:
 if jid:
  with Session(DB_ENGINE) as db:
   for model in (ScenicArrival,ScenicReview):
    for row in db.exec(select(model).where(model.journey_id==jid)).all():db.delete(row)
   row=db.get(ScenicJourney,jid)
   if row:db.delete(row)
   db.commit()
