import asyncio
import json
from unittest.mock import AsyncMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from server.base.routers import health
from server.base.modules.walk_access import pedestrian_access_allowed
from server.base.modules.answer_evidence import verify_answer, _CACHE
from server.base.modules import walking_network as roads
app = FastAPI()
app.include_router(health.router)
client = TestClient(app)

def test_readiness():
    assert client.get('/health/live').status_code == 200
    with patch.object(health, 'probe_database', side_effect=RuntimeError('secret')):
        response=client.get('/health/ready')
        assert response.status_code==503 and 'secret' not in response.text
    with patch.object(health, 'probe_database', return_value=0):
        assert client.get('/health/ready').status_code==503
    with patch.object(health, 'probe_database', return_value=16), patch.object(health, 'rag_available', return_value=False):
        response=client.get('/health/ready')
        assert response.status_code==200 and response.json()['rag']=='unavailable'

def test_node_access():
    for tags in ({'access':'private'},{'foot':'private'},{'locked':'yes'},{'barrier':'wall'}):
        assert not pedestrian_access_allowed(tags,node=True)
    assert pedestrian_access_allowed({'access':'private','foot':'yes'},node=True)
    assert not pedestrian_access_allowed({'access':'yes','foot':'no'},node=True)
    assert pedestrian_access_allowed({'barrier':'gate'},node=True)
    assert not pedestrian_access_allowed({'construction':'footway'})

def test_restricted_snapshot_edge():
    roads._path.cache_clear()
    try:
        with patch.object(roads,'ADJ',{1:[(2,0)],2:[(1,0)]}), patch.object(roads,'NETWORK',{'edges':[{'way_id':1,'meters':10,'steps':False,'access':'private'}]}):
            assert roads._path(1,2,False,()) is None
    finally: roads._path.cache_clear()

def test_relevance_and_question_specific_cache():
    _CACHE.clear()
    review={'answers_question':False,'checks':[{'segment':1,'supported':True,'quotes':[{'evidence_id':'local','quote':'长廊全长728米。'}]}]}
    model=AsyncMock(return_value=json.dumps(review,ensure_ascii=False))
    result=asyncio.run(verify_answer('长廊全长728米。','长廊全长728米。',[],model,question='长廊今天开放吗？'))
    assert result['status']=='rejected'
    review['answers_question']=True
    model.return_value=json.dumps(review,ensure_ascii=False)
    result=asyncio.run(verify_answer('长廊全长728米。','长廊全长728米。',[],model,question='长廊有多长？'))
    assert result['status']=='model_checked' and model.await_count==2


def test_review_evidence_matches_truncated_generation_context():
    from server.base.modules.rag.rag_worker import LightweightTourRetriever
    retriever=LightweightTourRetriever([('facts.md','<!-- spot:长廊;topic:history -->\n长廊全长728米。' * 20)])
    chunks,context,refs,evidence=retriever.query('长廊全长',context_max_length=100,spot_name='长廊',include_evidence=True)
    assert evidence and len(context)<=100
    assert all(e['excerpt'] in context and e['document'] in refs for e in evidence)
