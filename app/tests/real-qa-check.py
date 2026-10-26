"""Manual API smoke check; creates and ends only its own anonymous QA tour."""
from pathlib import Path
import json, urllib.request, urllib.parse

base='http://127.0.0.1:18000/api/v1'
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def call(path,method='GET',data=None):
    body=json.dumps(data).encode() if data is not None else b'' if method in ('POST','PUT') else None
    req=urllib.request.Request(base+path,data=body,method=method,headers={'Content-Type':'application/json'})
    with opener.open(req,timeout=110) as r:return json.load(r)
sid=None;report=dict(mocked=False,phone_verified=False,checks=[])
try:
    result=call('/tour-session/visitor-create?'+urllib.parse.urlencode(dict(name='App QA smoke check',guide_id=2,spot_ids='[12]')),'POST')
    assert result['success'];sid=result['data']['session_id']
    for question in ('Where is Jade Belt Bridge?', 'Tell me more about its history.'):
        r=call('/tour-session/chat','PUT',dict(sessionId=sid,message=question,currentSpotId=12,nextSpotId=None,language='en',text_only=True))
        assert r['success'] and r['data']['message'] and r['data']['language']=='en' and 'spot_ids' not in r['data']
        report['checks'].append(dict(question_uses_chat=True,language=r['data']['language'],answer_mode=r['data'].get('answerMode'),same_session=True))
    live=call('/tour-session/live-info/'+str(sid))['data'];assert len(live['conversation'])>=4
    report['checks'].append(dict(server_conversation_persisted=True))
    report['passed']=True
finally:
    if sid:report['test_tour_closed']=call('/tour-session/end/'+str(sid),'PUT').get('success')
    output=Path(__file__).resolve().parents[1]/'unpackage/main-d31183c-1.2.9/real-qa-check.json';output.parent.mkdir(parents=True,exist_ok=True);output.write_bytes(json.dumps(report,ensure_ascii=False,indent=2).encode());print(json.dumps(report))
