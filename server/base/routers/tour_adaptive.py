"""Preview and explicitly commit route repairs. Signed, short-lived proposals.

The session capability is the same one issued when choosing a digital guide.
Commit locks both the tour and progress row and rejects changed/expired plans.
"""
import json
import time
import re
from typing import Literal
import jwt
from fastapi import APIRouter, Header, HTTPException, BackgroundTasks, Request
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from ...web_configs import WEB_CONFIGS
from ..database.init_db import DB_ENGINE
from ..database.tour_session_db import _session_route_spots, _answer_metadata
from ..models.tour_models import TourSessionInfo, TourSessionStatus, ScenicSpotInfo, TourRoute
from ..modules.adaptive_itinerary import digest, parse_change, repair_route
from ..modules.xingyun_access import authorize_tour
from ..utils import make_return_data, ResultCode
from ..modules.tour_requests import run_turn
from ..modules.walking_network import network_version

router = APIRouter(prefix='/tour-session', tags=['tour-session'])

class RepairRequest(BaseModel):
    message: str = Field(default='', max_length=2000)
    remaining_minutes: int | None = Field(default=None, ge=1, le=480)
    pace: Literal['standard', 'relaxed'] = 'standard'
    end_area: Literal['auto', 'east', 'north', 'south'] = 'auto'
    excluded_spot_ids: list[int] = Field(default_factory=list, max_length=20)
    reserve_minutes: int = Field(default=0, ge=0, le=120)
    scenario: Literal['time', 'less_walking', 'skip', 'exit'] = 'time'
    strategy: Literal['highlights', 'shortest'] = 'highlights'
    required_spot_ids: list[int] = Field(default_factory=list, max_length=20)
    avoid_steps: bool = False
    allow_reorder: bool = True

class ApplyRequest(BaseModel):
    proposal_token: str = Field(max_length=12000)

@router.post('/{session_id}/reply/{message_id}/media')
async def reply_media(session_id: int, message_id: int, background_tasks: BackgroundTasks, request: Request,
                      x_tour_access: str = Header(default=''), authorization: str = Header(default='')):
    from ..models.tour_models import VisitorInteraction
    from ..database.tour_session_db import get_session_live_info
    from ..modules.reply_media import prepare_reply_media
    with Session(DB_ENGINE) as db:
        tour = db.get(TourSessionInfo, session_id)
        if not tour: raise HTTPException(404, '导览不存在')
        authorize_tour(db, session_id, tour.guide_id, x_tour_access, authorization)
        message = db.get(VisitorInteraction, message_id)
        if not message or message.session_id != session_id or message.role != 'guide':
            raise HTTPException(404, '答复不存在')
        meta = _answer_metadata(message.answer_metadata)
        if meta.get('textOnly'): raise HTTPException(409, '本轮为仅文字模式')
        latest = db.exec(select(VisitorInteraction).where(VisitorInteraction.session_id == session_id).order_by(VisitorInteraction.message_id.desc())).first()
        if not latest or latest.message_id != message_id: raise HTTPException(409, '已有新的对话，本轮语音已停止')
        text = meta.get('spokenText', message.message)
    live = await get_session_live_info(session_id)
    async def generate():
        media = await prepare_reply_media(live['guide_info'], session_id, message_id, text,
            meta.get('avatarMode','audio'), meta.get('language','zh'), background_tasks)
        return make_return_data(True, ResultCode.SUCCESS, '成功', media)
    return await run_turn(('media',session_id), request, generate)

def load_state(db, sid, access, auth, lock=False):
    tour = db.exec(select(TourSessionInfo).where(TourSessionInfo.session_id == sid).with_for_update()).first() if lock else db.get(TourSessionInfo, sid)
    if not tour or tour.delete: raise HTTPException(404, '导览不存在')
    authorize_tour(db, sid, tour.guide_id, access, auth)
    status = db.exec(select(TourSessionStatus).where(TourSessionStatus.status_id == tour.status_id).with_for_update()).one()
    if status.live_status == 2: raise HTTPException(409, '导览已结束，请重新开始')
    route, error = _session_route_spots(db, tour, db.get(TourRoute, tour.route_id) if tour.route_id else None)
    if error: raise HTTPException(409, error)
    catalog = db.exec(select(ScenicSpotInfo).where(ScenicSpotInfo.delete == False).order_by(ScenicSpotInfo.spot_id)).all()
    state = dict(route=[s.model_dump() for s in route], index=status.current_spot_index,
                 preferences=tour.visitor_preferences, catalog=[s.model_dump() for s in catalog])
    return tour, status, state

def calculate(state, options):
    prefs = _answer_metadata(state['preferences'])
    return repair_route(state['route'], state['index'], state['catalog'], options['remaining_minutes'],
                        options['pace'], options['end_area'], options['excluded_spot_ids'],
                        prefs.get('preferences', prefs.get('prefs', [])), options['reserve_minutes'],
                        required=options.get('required_spot_ids', []), avoid_steps=options.get('avoid_steps', False),
                        scenario=options.get('scenario', 'time'), strategy=options.get('strategy', 'highlights'),
                        allow_reorder=options.get('allow_reorder', True),
                        original_plan=prefs.get('last_replan') or prefs.get('planning') or {})

@router.post('/{session_id}/replan/preview')
async def preview(session_id: int, body: RepairRequest, x_tour_access: str = Header(default=''), authorization: str = Header(default='')):
    with Session(DB_ENGINE) as db:
        _, _, state = load_state(db, session_id, x_tour_access, authorization)
        options = body.model_dump(exclude={'message'})
        parsed = parse_change(body.message)
        for key, target in [('remaining_minutes', 'remaining_minutes'), ('pace', 'pace'), ('exit_area', 'end_area')]:
            if parsed[key] is not None: options[target] = parsed[key]
        if re.search(r'避开.*台阶|不想爬|avoid stairs|step.free',body.message,re.I) and not re.search(r'不要避开|do not avoid',body.message,re.I): options['avoid_steps']=True
        if options['remaining_minutes'] is None and options['scenario']=='time': raise HTTPException(422, '请填写剩余时间，再生成方案')
        if parsed['skip_next'] and state['index'] + 1 < len(state['route']):
            options['excluded_spot_ids'].append(state['route'][state['index'] + 1]['spot_id'])
        from ..modules.tour_language import ENGLISH_SPOT_NAMES
        for spot in state['route'][state['index'] + 1:]:
            names='(?:'+ '|'.join(re.escape(n) for n in [spot['spot_name'],ENGLISH_SPOT_NAMES.get(spot['spot_name'],'')] if n)+')'
            if not re.search(r'不要跳过|不用跳过|不要避开|do not skip|don.t skip',body.message,re.I) and re.search(r'(?:不去|不想去|跳过|避开|skip|avoid)\s*' + names, body.message, re.I):
                options['excluded_spot_ids'].append(spot['spot_id'])
            if not re.search(r'不要保留|不用保留|do not keep|don.t keep',body.message,re.I) and re.search(r'(?:必须保留|一定要去|保留|must (?:visit|keep)|keep|retain)\s*'+names,body.message,re.I):
                options['required_spot_ids'].append(spot['spot_id'])
        options['required_spot_ids']=sorted(set(options['required_spot_ids']))
        options['excluded_spot_ids']=sorted(set(options['excluded_spot_ids']))
        try:
            options = RepairRequest(**options).model_dump(exclude={'message'})
            result = calculate(state, options)
        except ValueError as exc: raise HTTPException(422, str(exc))
        now = int(time.time())
        def sign(plan, plan_options):
            token = jwt.encode(dict(purpose='route-repair', sid=session_id, state=digest(state), options=plan_options,
                network_version=network_version(), iat=now, exp=now+600), WEB_CONFIGS.TOKEN_JWT_SECURITY_KEY, algorithm='HS256')
            plan.update(proposal_token=token if plan['feasible'] else '', expires_at=now+600,
                        parsed_from_message=bool(body.message), options=plan_options)
            return plan
        if options['scenario']=='less_walking' and options['strategy']=='highlights':
            options['strategy']='shortest'; result=calculate(state, options)
        result=sign(result, options)
        alternatives=[]
        if options['scenario']!='exit':
            other_options=dict(options, strategy='highlights' if options['strategy']=='shortest' else 'shortest')
            other=calculate(state, other_options)
            if other['feasible'] and other['spot_ids']!=result['spot_ids']:
                alternatives.append(sign(other, other_options))
        result['alternatives']=alternatives
        return make_return_data(True, ResultCode.SUCCESS, '成功', result)

@router.post('/{session_id}/replan/apply')
async def apply(session_id: int, body: ApplyRequest, x_tour_access: str = Header(default=''), authorization: str = Header(default='')):
    try:
        claims = jwt.decode(body.proposal_token, WEB_CONFIGS.TOKEN_JWT_SECURITY_KEY, algorithms=['HS256'])
        if claims.get('purpose') != 'route-repair' or claims.get('sid') != session_id: raise ValueError()
    except (jwt.PyJWTError, ValueError): raise HTTPException(409, '方案已过期，请重新生成')
    with Session(DB_ENGINE) as db:
        tour, status, state = load_state(db, session_id, x_tour_access, authorization, lock=True)
        if digest(state) != claims['state']: raise HTTPException(409, '路线或进度已变化，请重新生成方案')
        if claims.get('network_version') != network_version(): raise HTTPException(409, '道路通行配置已变化，请重新生成方案')
        result = calculate(state, claims['options'])
        elapsed = max(0, int((time.time() - claims['iat']) // 60))
        if not result['feasible'] or result['remaining_minutes'] is not None and result['totals']['total_minutes'] + elapsed > result['remaining_minutes']:
            raise HTTPException(409, '剩余时间已不足，请重新生成方案')
        prefs = _answer_metadata(tour.visitor_preferences)
        prefs['spot_ids'] = result['spot_ids']
        prefs['route_revision'] = int(prefs.get('route_revision', 0)) + 1
        prefs['last_replan'] = {k: v for k, v in result.items() if k != 'note'}
        prefs['last_replan']['applied_at'] = int(time.time())
        if prefs['last_replan']['remaining_minutes'] is not None: prefs['last_replan']['remaining_minutes'] -= elapsed
        prefs['replan_history'] = (prefs.get('replan_history', []) + [dict(at=int(time.time()),
            before=[s['spot_id'] for s in state['route']], after=result['spot_ids'], current_index=status.current_spot_index)])[-20:]
        tour.visitor_preferences = json.dumps(prefs, ensure_ascii=False)
        db.add(tour); db.commit()
    return make_return_data(True, ResultCode.SUCCESS, '路线已更新', result)
