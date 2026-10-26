"""Real PostgreSQL/API checks with an isolated cloud adapter (no paid calls)."""
import json
import shutil
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from sqlmodel import Session, select
from server.base.base_server import app
from server.base.database.init_db import DB_ENGINE
from server.base.models.motion_job import MotionJob
from server.base.models.tour_models import DigitalGuideInfo
from server.base.routers.users import get_current_user_info
from server.base.modules import motion_provider

client = TestClient(app)
assert client.get('/avatar/motion/12').status_code == 401
with Session(DB_ENGINE) as db:
    guide=db.get(DigitalGuideInfo,12)
    owner=guide.user_id
    original_source, original_metadata=guide.base_mp4_path,guide.base_video_metadata
job_id=None
async def download(url,target):
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile('static/digital_guide/sources/musetalk-official-sun.mp4',target)
try:
    app.dependency_overrides[get_current_user_info]=lambda:owner
    with patch.object(motion_provider,'configured',return_value=False):
        assert client.post('/avatar/motion/12',json={}).status_code == 503
    with patch.object(motion_provider,'configured',return_value=True), patch.object(motion_provider,'submit',new=AsyncMock(return_value='isolated-test-task')) as submit:
        first=client.post('/avatar/motion/12',json={});assert first.status_code==200,first.text
        job_id=first.json()['data']['job_id']
        second=client.post('/avatar/motion/12',json={})
        assert second.json()['data']['job_id']==job_id and submit.await_count==1
    app.dependency_overrides[get_current_user_info]=lambda:owner+100000
    assert client.post('/avatar/motion-jobs/'+job_id+'/refresh').status_code==404
    assert client.post('/avatar/motion-jobs/'+job_id+'/apply').status_code==404
    app.dependency_overrides[get_current_user_info]=lambda:owner
    with patch.object(motion_provider,'query',new=AsyncMock(return_value={'task_status':'RUNNING'})):
        assert client.post('/avatar/motion-jobs/'+job_id+'/refresh').json()['data']['status']=='running'
    with patch.object(motion_provider,'query',new=AsyncMock(return_value={'task_status':'SUCCEEDED','video_url':'isolated-test'})),patch.object(motion_provider,'download',new=download):
        response=client.post('/avatar/motion-jobs/'+job_id+'/refresh');assert response.status_code==200,response.text
        assert response.json()['data']['status']=='completed'
    result=client.post('/avatar/motion-jobs/'+job_id+'/apply');assert result.status_code==200,result.text
    with Session(DB_ENGINE) as db:
        guide=db.get(DigitalGuideInfo,12)
        assert guide.base_mp4_path.endswith(job_id+'.mp4')
        assert json.loads(guide.base_video_metadata)['kind']=='motion_candidate'
    assert client.post('/avatar/motion-jobs/'+job_id+'/apply').status_code==200
    print('PASS: unconfigured gate, task persistence, duplicate submission, ownership, query, decode, apply, idempotence')
finally:
    app.dependency_overrides.clear()
    with Session(DB_ENGINE) as db:
        guide=db.get(DigitalGuideInfo,12);guide.base_mp4_path=original_source;guide.base_video_metadata=original_metadata;db.add(guide)
        if job_id:
            job=db.get(MotionJob,job_id)
            if job:db.delete(job)
        db.commit()
    if job_id:(Path('static/digital_guide/sources')/('motion-'+job_id+'.mp4')).unlink(missing_ok=True)
