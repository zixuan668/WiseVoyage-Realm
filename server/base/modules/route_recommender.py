"""Preference planning grounded in curated features and a park walking network."""
import json
import math
import re
from pathlib import Path
from .route_city import spot_city, normalize_city

DATA=Path(__file__).resolve().parents[3]/'data'
CATALOG=json.loads((DATA/'summer_palace_profiles.json').read_text(encoding='utf-8'))
LOCATIONS=json.loads((DATA/'summer_palace_locations.json').read_text(encoding='utf-8'))['spots']
WALKS=json.loads((DATA/'summer_palace_walk_distances.json').read_text(encoding='utf-8'))
LABELS={'history':'历史文化','nature':'自然风光','photography':'影像记录','family':'亲子游览','comprehensive':'综合游览'}
ALGORITHM_VERSION='curated-features-exit-budget-v5'
PREFERENCE_CATEGORY_MAP={'history':['historical','cultural'],'nature':['natural'],'photography':['cultural','natural'],'family':['comprehensive'],'comprehensive':['historical','cultural','natural','modern','comprehensive']}
PREFERENCE_TAG_KEYWORDS={'history':['历史','古建筑','文化'],'nature':['自然','湖景','植物'],'photography':['摄影','拍照','倒影'],'family':['亲子','科普','互动']}

def _get_value(spot,field,default=None):
    return spot.get(field,default) if isinstance(spot,dict) else getattr(spot,field,default)

def _haversine_meters(a,b):
    values=[float(_get_value(s,f,0) or 0) for s in (a,b) for f in ('latitude','longitude')]
    if not all(values): return float('inf')
    lat1,lng1,lat2,lng2=map(math.radians,values)
    return 12742000*math.asin(min(1,math.sqrt(math.sin((lat2-lat1)/2)**2+math.cos(lat1)*math.cos(lat2)*math.sin((lng2-lng1)/2)**2)))

def get_spot_profile(spot):
    name=_get_value(spot,'spot_name','')
    if spot_city(spot)=='北京' and name in LOCATIONS and _haversine_meters(spot,LOCATIONS[name])<150:
        return CATALOG['profiles'].get(name)
    return None

def normalize_preferences(preferences):
    valid=list(dict.fromkeys(p for p in preferences if p in LABELS))
    return ['comprehensive'] if not valid or 'comprehensive' in valid else valid

def get_recommended_categories(preferences):
    return list(dict.fromkeys(c for p in normalize_preferences(preferences) for c in PREFERENCE_CATEGORY_MAP[p]))

def get_primary_theme(preferences):
    return normalize_preferences(preferences)[0]

def _features(spot):
    profile=get_spot_profile(spot)
    if profile:return profile
    tags=str(_get_value(spot,'tags',''));category=_get_value(spot,'category','')
    affinities={p:min(5,(3 if category in PREFERENCE_CATEGORY_MAP[p] else 0)+sum(k in tags for k in words)) for p,words in PREFERENCE_TAG_KEYWORDS.items()}
    reasons={p:f"已配置分类与标签：{tags or category}" for p,v in affinities.items() if v>=3}
    return {'affinities':affinities,'stairs':any(k in tags for k in ('登山','台阶','爬山')),'reasons':reasons}

def _distance(a,b,avoid_steps=False):
    if get_spot_profile(a) and get_spot_profile(b):
        from .walking_network import distance_between
        return distance_between(a,b,avoid_steps)
    return _haversine_meters(a,b)*1.5

async def recommend_route(preferences,spot_list,time_budget_minutes=None,city='',pace='standard',start_area='auto',
                          end_area='auto', queue_reserve_minutes=0, excluded_spot_ids=None):
    preferences=normalize_preferences(preferences)
    budget=max(15,min(480,int(time_budget_minutes or 120)))
    pace='relaxed' if pace=='relaxed' or 'family' in preferences else 'standard'
    groups={}
    for spot in spot_list:
        c=spot_city(spot)
        if c:groups.setdefault(c,[]).append(spot)
    selected_city=normalize_city(city)
    if not selected_city and groups:
        # Choose a feasible city from actual data instead of blindly using the
        # largest group, which can have no matches or exceed the time budget.
        plans=[await recommend_route(preferences,spot_list,budget,c,pace,start_area,
            end_area,queue_reserve_minutes,excluded_spot_ids) for c in sorted(groups)]
        return max(plans,key=lambda p:(bool(p['spot_ids']),
            len({pref for detail in p['score_details'] for pref in detail['matched_preferences']}),
            sum(detail['score'] for detail in p['score_details']),p['spot_count']))
    spots=groups.get(selected_city,[])
    all_profiles=bool(spots) and all(get_spot_profile(s) for s in spots)
    start_name={'east':'仁寿殿','north':'苏州街','south':'铜牛'}.get(start_area)
    origin=next((s for s in spots if _get_value(s,'spot_name')==start_name and get_spot_profile(s)),None)
    end_name={'east':'仁寿殿','north':'苏州街','south':'铜牛'}.get(end_area)
    destination=next((s for s in spots if _get_value(s,'spot_name')==end_name and get_spot_profile(s)),None)
    queue_reserve=max(0,min(120,int(queue_reserve_minutes or 0)))
    excluded=set(excluded_spot_ids or [])
    candidates=[]; stair_excluded=0
    for spot in spots:
        if _get_value(spot,'spot_id') in excluded: continue
        profile=_features(spot)
        if (pace=='relaxed' or 'family' in preferences) and profile['stairs']:
            stair_excluded+=1;continue
        active=list(PREFERENCE_TAG_KEYWORDS) if preferences==['comprehensive'] else preferences
        matches=[p for p in active if profile['affinities'][p]>=3]
        if not matches:continue
        score=sum(profile['affinities'][p] for p in active)/len(active)*20
        candidates.append({'spot':spot,'score':score,'profile':profile,'matched':matches})
    from .walking_network import gate_distance, NETWORK
    avoid_steps = pace=='relaxed'
    speed=55 if pace=='relaxed' else 75
    def totals(route):
        visit=sum(int(_get_value(i['spot'],'visit_duration',10) or 10) for i in route)
        legs=[_distance(a['spot'],b['spot'],avoid_steps) for a,b in zip(route,route[1:])]
        if origin and route:legs.insert(0,gate_distance(route[0]['spot'],start_area,avoid_steps))
        exit_meters=gate_distance(route[-1]['spot'],end_area,avoid_steps) if destination and route else 0
        exit_minutes=(math.ceil(exit_meters/speed) if math.isfinite(exit_meters) else float('inf')) if destination and route else 0
        meters=sum(legs)
        walk=sum(math.ceil(leg/speed) for leg in legs) if math.isfinite(meters) else float('inf')
        rest=math.ceil((visit+walk+exit_minutes)*(0.15 if speed==55 else 0.08)) if route and math.isfinite(walk+exit_minutes) else 0
        return visit,walk,rest,meters,visit+walk+rest+exit_minutes+(queue_reserve if route else 0),exit_minutes,exit_meters
    selected=[]; remaining=candidates.copy(); coverage={p:0 for p in PREFERENCE_TAG_KEYWORDS}
    while remaining and len(selected)<8:
        feasible=[]; old_total=totals(selected)[4]
        for item in remaining:
            for index in range(len(selected)+1):
                route=selected[:index]+[item]+selected[index:]
                total=totals(route)[4]
                if total>budget:continue
                balance=sum(10/(1+coverage[p]) for p in item['matched'])
                utility=(item['score']+balance)/((total-old_total+12)**0.65)
                feasible.append((utility,-total,-int(_get_value(item['spot'],'spot_id',0)),index,item))
        if not feasible:break
        _,_,_,index,best=max(feasible,key=lambda f:f[:3])
        selected.insert(index,best);remaining.remove(best)
        for p in best['matched']:coverage[p]+=1
    visit,walk,rest,meters,total,exit_minutes,exit_meters=totals(selected)
    details=[]
    for index,item in enumerate(selected):
        previous=selected[index-1]['spot'] if index else origin
        leg=(round(_distance(previous,item['spot'],avoid_steps)) if index else gate_distance(item['spot'],start_area,avoid_steps)) if previous else 0
        reasons=[item['profile']['reasons'][p] for p in item['matched'] if p in item['profile']['reasons']]
        details.append({'spot_id':_get_value(item['spot'],'spot_id'),'spot_name':_get_value(item['spot'],'spot_name'),
            'score':round(item['score'],1),'diversity_penalty':0,'components':item['profile']['affinities'],
            'matched_preferences':item['matched'],'reason':'；'.join(reasons[:2]),'walk_from_previous_minutes':math.ceil(leg/speed),'walk_from_previous_meters':leg})
    basis='依据景点特色人工标注和园内步行路网；不是游客行为预测。' if all_profiles else '依据已配置的景点分类与标签；部分步行距离按直线距离的 1.5 倍估算。'
    explanation=f'从 {len(spots)} 个景点中筛出 {len(candidates)} 个兴趣匹配且适合当前节奏的候选，选入 {len(selected)} 个；停留、步行、休息、离园和预留合计 {total} / {budget} 分钟。'
    if stair_excluded: explanation+=f'避开 {stair_excluded} 个台阶较多的景点。'
    return {'city':selected_city,'name':' · '.join(LABELS[p] for p in preferences)+'路线','theme':get_primary_theme(preferences),'description':basis,
        'preferences':preferences,'avoid_steps':avoid_steps,'pace':pace,'start_area':start_area if origin else 'auto','start_label':NETWORK['gates'][start_area]['label'] if origin else '首个景点起步',
        'spot_ids':[_get_value(i['spot'],'spot_id') for i in selected],'spot_names':[_get_value(i['spot'],'spot_name') for i in selected],
        'spot_count':len(selected),'candidate_count':len(candidates),'catalog_count':len(spots),'stairs_excluded_count':stair_excluded,
        'estimated_time_minutes':total,'visit_time_minutes':visit,'walking_time_minutes':walk,'rest_time_minutes':rest,'walking_distance_meters':round(meters),
        'exit_time_minutes':exit_minutes,'exit_distance_meters':round(exit_meters),'end_area':end_area if destination else 'auto',
        'end_label':NETWORK['gates'][end_area]['label']+'离园' if destination else '末站结束（未计离园）','queue_reserve_minutes':queue_reserve if selected else 0,
        'excluded_spot_ids':sorted(excluded & {_get_value(s,'spot_id') for s in spots}),
        'accessibility_status':'避开已标注台阶路段及多台阶景点；未标注障碍和实时开放状态仍需现场确认，不是无障碍路线认证。',
        'requested_time_minutes':budget,'excluded_spot_count':len(spots)-len(selected),'algorithm_version':ALGORITHM_VERSION,
        'recommendation_explanation':explanation,'data_basis':basis,'planning_note':
        ('离园沿园内路网计算至所选出口，未额外虚加接近出口的固定时间。' if destination else '未选择离园区域，预算只覆盖至末站。')
        +'排队预留由游客设置，不是实时客流。步行、停留和休息均为估算，不含船渡；开放与通行以现场为准。',
        'source_urls':CATALOG['source_urls']+(['https://www.openstreetmap.org/copyright'] if all_profiles else []),'score_details':details}

def parse_preferences_from_message(message):
    words={'history':['历史','文化','故事','古迹','建筑'],'nature':['自然','风景','山水','风光','花草','湖景'],
           'photography':['拍照','打卡','摄影','照片'],'family':['孩子','小孩','亲子','家庭','带娃','儿童']}
    found=[]
    for pref,keywords in words.items():
        for keyword in keywords:
            for match in re.finditer(re.escape(keyword),message):
                if not re.search(r'(不喜欢|不想|不要|不看|不爱|不需|不)[^，。；、]{0,3}$',message[max(0,match.start()-7):match.start()]):
                    found.append(pref);break
            if pref in found:break
    return found or ['comprehensive']

def verified_model_summary(result, payload, known_names):
    """A model explanation cannot replace the planner's verified itinerary."""
    if not isinstance(payload,dict) or payload.get('spot_ids')!=result['spot_ids'] or payload.get('estimated_time_minutes')!=result['estimated_time_minutes']:
        return None
    summary=payload.get('summary','')
    if not isinstance(summary,str) or not summary.strip() or len(summary)>200:return None
    if any(name in summary and name not in result['spot_names'] for name in known_names):return None
    if any(word in summary for word in ('天气','门票','开放时间','排队','实时客流')):return None
    return summary.strip()

def parse_time_budget_from_message(message):
    text=(message or '').lower().replace('个','')
    if '半天' in text:return 240
    if '一天' in text or '1天' in text:return 360
    hour=re.search(r'(\d+(?:\.\d+)?)\s*(?:小时|钟头|h\b)',text)
    if hour:return max(15,min(480,int(float(hour.group(1))*60)+(30 if '半' in text[hour.end():hour.end()+1] else 0)))
    chinese=re.search(r'([半一两二三四五六])\s*(?:小时|钟头)(半)?',text)
    if chinese:return int({'半':.5,'一':1,'两':2,'二':2,'三':3,'四':4,'五':5,'六':6}[chinese.group(1)]*60)+(30 if chinese.group(2) else 0)
    minute=re.search(r'(\d+)\s*(?:分钟|min\b)',text)
    if minute:return max(15,min(480,int(minute.group(1))))
    chinese_minute=re.search(r'([一二两三四五六七八九十]+)\s*分钟',text)
    if chinese_minute:
        digits={'一':1,'二':2,'两':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9};raw=chinese_minute.group(1)
        if '十' in raw:
            left,right=raw.split('十',1);value=digits.get(left,1)*10+digits.get(right,0)
        else:value=digits.get(raw,0)
        return max(15,value) if value else None
    return None
