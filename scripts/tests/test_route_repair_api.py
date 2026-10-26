"""Exercise real signed preview/apply endpoints against an isolated SQLite tour."""
import json
import unittest
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine
from server.base.models.tour_models import ScenicSpotInfo, TourSessionInfo, TourSessionStatus, DigitalGuideInfo
from server.base.routers import tour_adaptive as api
from server.base.modules.xingyun_access import issue_tour_avatar_token
from test_preference_planner import SPOTS


class SignedRouteRepairTests(unittest.TestCase):
    def setUp(self):
        self.key_patch=patch.object(api.WEB_CONFIGS,'TOKEN_JWT_SECURITY_KEY','isolated-route-test-signing-key-32bytes')
        self.key_patch.start()
        self.engine=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
        SQLModel.metadata.create_all(self.engine)
        with Session(self.engine) as db:
            for s in SPOTS:
                db.add(ScenicSpotInfo(spot_id=s['spot_id'],spot_name=s['spot_name'],city='北京',
                    latitude=s['latitude'],longitude=s['longitude'],visit_duration=s['visit_duration']))
            db.add(DigitalGuideInfo(guide_id=11,name='文轩'))
            status=TourSessionStatus(current_spot_index=1)
            db.add(status);db.commit()
            tour=TourSessionInfo(name='isolated-route-test',status_id=status.status_id,guide_id=11,
                visitor_preferences=json.dumps({'spot_ids':[1,2,3,4,5,6]}))
            db.add(tour);db.commit();db.refresh(tour)
            self.sid=tour.session_id;self.status_id=status.status_id
            self.headers={'X-Tour-Access':issue_tour_avatar_token(tour)}
        self.patch=patch.object(api,'DB_ENGINE',self.engine);self.patch.start()
        app=FastAPI();app.include_router(api.router);self.client=TestClient(app)
        self.base=f'/tour-session/{self.sid}/replan'

    def tearDown(self):
        self.client.close();self.patch.stop();self.key_patch.stop();self.engine.dispose()

    def preview(self,**kwargs):
        response=self.client.post(self.base+'/preview',headers=self.headers,json=dict(remaining_minutes=150,end_area='east',**kwargs))
        self.assertEqual(response.status_code,200,response.text[:200])
        return response.json()['data']

    def apply(self,plan):
        return self.client.post(self.base+'/apply',headers=self.headers,json={'proposal_token':plan['proposal_token']})

    def test_preview_is_read_only_and_replay_cannot_commit_twice(self):
        p=self.preview(excluded_spot_ids=[3],required_spot_ids=[4])
        with Session(self.engine) as db:
            self.assertEqual(json.loads(db.get(TourSessionInfo,self.sid).visitor_preferences)['spot_ids'],[1,2,3,4,5,6])
        self.assertEqual(self.apply(p).status_code,200)
        self.assertEqual(self.apply(p).status_code,409)
        with Session(self.engine) as db:
            tour=db.get(TourSessionInfo,self.sid);status=db.get(TourSessionStatus,self.status_id)
            ids=json.loads(tour.visitor_preferences)['spot_ids']
            self.assertEqual(ids[:2],[1,2]);self.assertIn(4,ids);self.assertNotIn(3,ids)
            self.assertEqual(status.current_spot_index,1)
            self.assertEqual(tour.guide_id,11)

    def test_network_changes_invalidate_an_already_signed_plan(self):
        p=self.preview()
        with patch.object(api,'network_version',return_value='changed-road-access'):
            response=self.apply(p)
        self.assertEqual(response.status_code,409)
        self.assertIn('通行配置',response.json()['detail'])

    def test_progress_changes_reject_stale_preview(self):
        p=self.preview()
        with Session(self.engine) as db:
            status=db.get(TourSessionStatus,self.status_id);status.current_spot_index=2;db.add(status);db.commit()
        self.assertEqual(self.apply(p).status_code,409)

    def test_no_time_limit_exit_and_english_required_stop_are_supported(self):
        response=self.client.post(self.base+'/preview',headers=self.headers,json={
            'scenario':'exit','end_area':'north','remaining_minutes':None})
        self.assertEqual(response.status_code,200)
        p=response.json()['data'];self.assertTrue(p['exit_only']);self.assertEqual(p['end_anchor'],'北宫门')
        p=self.preview(message='keep Kunming Lake and skip Tower of Buddhist Incense')
        self.assertIn(4,p['options']['required_spot_ids'])
        self.assertIn(3,p['options']['excluded_spot_ids'])

    def test_alternative_plan_is_individually_signed_and_can_be_applied(self):
        p=self.preview()
        self.assertTrue(p['alternatives'])
        alt=p['alternatives'][0]
        self.assertNotEqual(p['proposal_token'],alt['proposal_token'])
        self.assertNotEqual(p['spot_ids'],alt['spot_ids'])
        self.assertEqual(self.apply(alt).status_code,200)

    def test_unauthorized_or_conflicting_requests_do_not_modify_tour(self):
        self.assertEqual(self.client.post(self.base+'/preview',json={'remaining_minutes':90}).status_code,401)
        response=self.client.post(self.base+'/preview',headers=self.headers,json={
            'remaining_minutes':90,'excluded_spot_ids':[4],'required_spot_ids':[4]})
        self.assertEqual(response.status_code,422)


if __name__=='__main__':unittest.main()
