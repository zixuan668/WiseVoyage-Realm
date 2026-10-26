"""Local API acceptance; creates only labelled disposable verification records.

No provider credentials/tokens are printed or saved. A temporary document is
withdrawn/deleted and the verification tour is ended in finally blocks.
"""
import json
from pathlib import Path
import requests

BASE='http://127.0.0.1:8000'
ROOT=Path(__file__).resolve().parents[1]


def call(method,path,**kwargs):
    response=requests.request(method,BASE+path,timeout=90,**kwargs)
    response.raise_for_status()
    body=response.json()
    assert body.get('success'),body.get('message')
    return body['data']


def main():
    result={}
    plan=call('POST','/tour-routes/recommend',json={
        'preferences':['nature','photography'],'time_budget_minutes':120,
        'start_area':'east','end_area':'north','queue_reserve_minutes':20})
    assert plan['estimated_time_minutes']<=120 and plan['exit_time_minutes']>=5
    result['plan']={k:plan[k] for k in ('spot_names','estimated_time_minutes','visit_time_minutes','walking_time_minutes','rest_time_minutes','exit_time_minutes','queue_reserve_minutes')}
    avoided=call('POST','/tour-routes/recommend',json={
        'preferences':['nature','photography'],'time_budget_minutes':120,'end_area':'north',
        'excluded_spot_ids':plan['spot_ids']})
    assert set(avoided['spot_ids']).isdisjoint(plan['spot_ids'])
    result['avoidance_passed']=True

    token_response=requests.post(BASE+'/user/login',data={'username':'admin','password':'123456'},timeout=15)
    token_response.raise_for_status()
    headers={'Authorization':'Bearer '+token_response.json()['access_token']}
    doc=None
    try:
        doc=call('POST','/knowledge-base/upload',headers=headers,data={'title':'本地审核流程验收（临时）'},
                 files={'file':('acceptance.md','<!-- spot:长廊;topic:history -->\n长廊全长728米。本文仅用于本地审核流程验收。'.encode(),'text/markdown')})['doc_id']
        preview=call('GET',f'/knowledge-base/preview/{doc}',headers=headers)
        assert preview['status']=='pending' and not preview['reviews']
        stale=requests.post(BASE+f'/knowledge-base/review/{doc}',headers=headers,json={
            'decision':'publish','note':'自动验收：版本不匹配应失败','expected_hash':'stale'},timeout=15).json()
        assert not stale['success']
        reviewed=call('POST',f'/knowledge-base/review/{doc}',headers=headers,json={
            'decision':'publish','note':'自动验收：仅验证审核流程，非人工事实审核','expected_hash':preview['expected_hash']})
        assert reviewed['status']=='completed' and reviewed['index_version']
        published=call('GET',f'/knowledge-base/preview/{doc}',headers=headers)
        assert len(published['reviews'])==1
        call('POST',f'/knowledge-base/review/{doc}',headers=headers,json={
            'decision':'withdraw','note':'自动验收结束，撤回临时文档','expected_hash':published['expected_hash']})
        result['review']={'pending_before_review':True,'stale_preview_rejected':True,'publication_index_version':reviewed['index_version'],'withdrawn':True}
    finally:
        if doc:call('DELETE',f'/knowledge-base/delete/{doc}',headers=headers)

    spots=call('GET','/tour-session/spots')['spot_list']
    by_name={s['spot_name']:s for s in spots}
    guides=call('GET','/tour-session/guides')['guide_list']
    sid=call('POST','/tour-session/visitor-create',params={
        'name':'痛点功能验收','guide_id':guides[0]['guide_id'],
        'spot_ids':json.dumps([by_name[n]['spot_id'] for n in ('长廊','昆明湖','十七孔桥')])})['session_id']
    result['session_id']=sid
    result['dialogue']=[]
    try:
        for question,options in [
            ('介绍长廊',{'explanation_mode':'child'}),
            ('长廊有哪些建筑特点？',{'explanation_mode':'deep'}),
            ('What is special about the Long Corridor?',{'language':'en'}),
            ('附近的卫生间在哪？',{}),
            ('长廊里外星文明的暗号是什么？',{}),
            ('长廊有多长？',{}),
            ('下一站去哪儿？',{'text_only':True}),
        ]:
            reply=call('PUT','/tour-session/chat',json={
                'sessionId':sid,'message':question,'currentSpotId':by_name['长廊']['spot_id'],
                'nextSpotId':by_name['昆明湖']['spot_id'],'avatarMode':'audio',**options})
            meta=reply['aiMeta']
            if 'explanation_mode' in options:assert meta['explanationMode']==options['explanation_mode']
            if options.get('language')=='en':
                import re
                assert not re.search(r'[\u4e00-\u9fff]',reply['message'])
            if '外星' in question:assert meta['answerMode']=='database' and not meta['evidence']
            if '卫生间' in question:assert meta['serviceActions'] and '核实' in reply['message']
            if options.get('text_only'):assert meta['textOnly'] and not reply['ttsAudioUrl']
            if meta['answerMode'].startswith('llm_'):assert meta['claimReview']['status']=='model_checked' and meta['claimReview']['checks']
            if meta['ragApplied']:assert meta['evidence'] and all(e['version'] for e in meta['evidence'])
            result['dialogue'].append({'question':question,'answer':reply['message'],'mode':meta['answerMode'],
                'language':meta['language'],'explanation':meta['explanationMode'],'numeric_guard':meta['numericGuard'],
                'review_status':meta['claimReview']['status'],'text_only':meta['textOnly'],
                'evidence_count':len(meta['evidence']),'audio_available':bool(reply['ttsAudioUrl'])})
        live=call('GET',f'/tour-session/live-info/{sid}')
        guide_messages=[message for message in live['conversation'] if message['role']=='guide']
        assert 'speechRate' not in guide_messages[-2]['aiMeta']
        assert guide_messages[-1]['aiMeta']['textOnly']
        result['persisted_metadata']=True
    finally:
        call('PUT',f'/tour-session/end/{sid}')
    (ROOT/'work_dirs/pain-point-acceptance.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
