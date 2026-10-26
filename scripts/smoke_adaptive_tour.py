"""Local acceptance smoke test. Requires running seeded backend on 127.0.0.1:8000.
Creates clearly named test tours and ends them in finally. Never prints tokens.
Run from repository root: .venv/Scripts/python.exe scripts/smoke_adaptive_tour.py
"""
import json,time,requests
from pathlib import Path
s=requests.Session();s.trust_env=False;base='http://127.0.0.1:8000/tour-session'
checks=[];sessions=[]
spots=s.get(base+'/spots').json()['data']['spot_list']
names={item['spot_name']:item['spot_id'] for item in spots}
guide_id=s.get(base+'/guides').json()['data']['guide_list'][0]['guide_id']
selected=[names[n] for n in ['仁寿殿','长廊','佛香阁','昆明湖','十七孔桥']]
def check(name,condition):
 assert condition,name
 checks.append(name);print('PASS',name,flush=True)
def create():
 r=s.post(base+'/visitor-create',params={'name':'three-module-api-QA','guide_id':guide_id,'spot_ids':json.dumps(selected),'planning':json.dumps({'time_budget_minutes':120,'end_area':'east'})});r.raise_for_status();d=r.json()['data'];sessions.append(d['session_id']);return d['session_id'],{'X-Tour-Access':d['avatar_access_token']}
def live(sid):return s.get(base+f'/live-info/{sid}').json()['data']
try:
 sid,h=create();other,otherh=create();before=live(sid)
 check('visitor session starts with saved planning',before['live_status']==1 and json.loads(before['visitor_preferences'])['planning']['time_budget_minutes']==120)
 check('remaining time is never guessed',s.post(base+f'/{sid}/replan/preview',json={'message':'我带了2个孩子，想少走一点'},headers=h).status_code==422)
 opts={'message':'累了，只剩40分钟，从东门离园'}
 url=base+f'/{sid}/replan/preview'
 check('missing capability rejected',s.post(url,json=opts).status_code==401)
 check('other session capability rejected',s.post(url,json=opts,headers=otherh).status_code==401)
 p=s.post(url,json=opts,headers=h);p.raise_for_status();p=p.json()['data']
 check('preview parses all spoken constraints',p['remaining_minutes']==40 and p['pace']=='relaxed' and p['end_area']=='east')
 check('preview never changes route',live(sid)['visitor_preferences']==before['visitor_preferences'])
 check('preview retains current stop and fits budget',p['spot_ids'][0]==selected[0] and p['totals']['total_minutes']<=40)
 r=s.post(base+f'/{sid}/replan/apply',json={'proposal_token':p['proposal_token']},headers=h);r.raise_for_status()
 after=live(sid)
 check('commit preserves guide and progress',after['current_spot_index']==before['current_spot_index'] and after['guide_info']['guide_id']==guide_id)
 check('commit updates route',json.loads(after['visitor_preferences'])['spot_ids']==p['spot_ids'])
 check('replay of applied proposal rejected',s.post(base+f'/{sid}/replan/apply',json={'proposal_token':p['proposal_token']},headers=h).status_code==409)
 check('proposal for another session rejected',s.post(base+f'/{other}/replan/apply',json={'proposal_token':p['proposal_token']},headers=otherh).status_code==409)
 for q,language,mode in [('清漪园为什么修建？','zh','historical'),('1860年这里发生了什么？','zh','modern_handoff'),('长廊的彩画是谁画的？','zh','insufficient'),('Why was Qingyi Yuan built?','en','historical')]:
  t=time.perf_counter();r=s.put(base+'/chat',json={'sessionId':sid,'message':q,'persona':'qianlong','language':language,'text_only':True,'defer_speech':True,'currentSpotId':selected[0],'avatarMode':'audio'},headers=h,timeout=90);r.raise_for_status();d=r.json()['data']
  check('history '+mode+' '+language,d['aiMeta']['persona']['mode']==mode)
  print('  reply',d['message'][:150],'elapsed',round(time.perf_counter()-t,2),flush=True)
 # Deferred speech endpoint should reject stale and text-only replies rather than replaying them.
 check('text-only media rejected',s.post(base+f"/{sid}/reply/{d['messageId']}/media",headers=h).status_code==409)
 r=s.put(base+'/chat',json={'sessionId':other,'message':'下一站在哪里？','persona':'modern','language':'zh','text_only':False,'defer_speech':True,'avatarMode':'audio'},headers=otherh,timeout=90);r.raise_for_status();d=r.json()['data']
 check('text delivered before synthesis',bool(d['message']) and d['speechPending'] and not d['ttsAudioUrl'])
 first_id=d['messageId']
 r=s.put(base+'/chat',json={'sessionId':other,'message':'长廊附近的厕所在哪里？','text_only':True},headers=otherh,timeout=90);r.raise_for_status()
 check('stale audio rejected after new question',s.post(base+f'/{other}/reply/{first_id}/media',headers=otherh).status_code==409)
 for q in ['十七孔桥为什么叫这个名字？','那它有多长？','它和刚才的长廊有什么区别？']:
  r=s.put(base+'/chat',json={'sessionId':other,'message':q,'currentSpotId':names['长廊'],'text_only':True},headers=otherh,timeout=90);r.raise_for_status();reply=r.json()['data']
  if q=='那它有多长？':check('specific follow-up stays on bridge and answers length',reply['aiMeta']['spotContext']=='十七孔桥' and '150' in reply['message'])
  if '区别' in q:check('comparison resolves both subjects','长廊' in reply['message'] and '十七孔桥' in reply['message'])
 check('discussion does not move itinerary',live(other)['current_spot_info']['spot_id']==selected[0])
 fresh=s.post(base+f'/{other}/replan/preview',json={'remaining_minutes':120},headers=otherh).json()['data']['proposal_token']
 check('advance succeeds',s.post(base+f'/next-spot/{other}',headers=otherh).json()['success'])
 check('progress change invalidates old preview',s.post(base+f'/{other}/replan/apply',json={'proposal_token':fresh},headers=otherh).status_code==409)
 Path('work_dirs/three-modules-api-results.json').write_text(json.dumps({'passed':checks,'count':len(checks)},ensure_ascii=False,indent=2),encoding='utf-8')
finally:
 for sid in sessions:s.put(base+f'/end/{sid}',timeout=10)
