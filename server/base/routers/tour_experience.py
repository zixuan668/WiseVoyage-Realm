"""Shared route geometry and order calculations for the station, admin and App."""
from typing import Literal
from uuid import uuid4
from fastapi import APIRouter, Header, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlmodel import Session, SQLModel, Field as Column, select

from ..database.init_db import DB_ENGINE
from ..models.tour_models import ScenicSpotInfo
from ..models.scenic_audio import ScenicAudio
from ..modules.route_city import route_city
from ..modules.route_presentation import route_overview
from ..utils import make_return_data, ResultCode
from .users import get_current_user_info

router = APIRouter(prefix='/tour-experience', tags=['tour-experience'])


class RoutePreviewRequest(BaseModel):
    spot_ids: list[int] = Field(default_factory=list, max_length=20)
    pace: Literal['standard', 'relaxed'] = 'standard'
    start_area: Literal['auto', 'east', 'north', 'south'] = 'auto'
    end_area: Literal['auto', 'east', 'north', 'south'] = 'auto'
    avoid_steps: bool = False
    reserve: int = Field(default=0, ge=0, le=120)


def load_spots(db, ids):
    if len(set(ids)) != len(ids):
        raise HTTPException(422, '路线中有重复景点')
    spots = [db.get(ScenicSpotInfo, sid) for sid in ids]
    if any(not s or s.delete for s in spots):
        raise HTTPException(422, '所选景点不可用')
    try:
        if spots: route_city(spots)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    return [s.model_dump() for s in spots]


@router.post('/route-preview')
def preview_route(body: RoutePreviewRequest):
    with Session(DB_ENGINE) as db:
        result = route_overview(load_spots(db, body.spot_ids), body.pace, end_area=body.end_area,
            start_area=body.start_area, avoid_steps=body.avoid_steps, reserve=body.reserve)
    return make_return_data(True, ResultCode.SUCCESS, '成功', result)


class RouteOrderRequest(RoutePreviewRequest):
    spot_ids: list[int] = Field(min_length=2, max_length=20)
    fixed_start: bool = True
    fixed_end: bool = False


@router.post('/optimize-order', summary='只调整景点顺序，保留全部已选景点')
def preview_order_optimization(body: RouteOrderRequest):
    from ..modules.route_order import optimize_order
    with Session(DB_ENGINE) as db:
        spots = load_spots(db, body.spot_ids)
    try:
        result = optimize_order(spots, fixed_start=body.fixed_start, fixed_end=body.fixed_end,
            pace=body.pace, start_area=body.start_area, end_area=body.end_area,
            avoid_steps=body.avoid_steps, reserve=body.reserve)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return make_return_data(True, ResultCode.SUCCESS, '成功', result)


class ScenicDraftStop(SQLModel, table=True):
    owner: str = Column(primary_key=True)
    spot_id: int = Column(primary_key=True)


def scenic_draft_owner(request: Request):
    authorization = request.headers.get('authorization', '')
    if authorization.lower().startswith('bearer '):
        user_id = get_current_user_info(authorization[7:].strip())
        return f'app:{user_id}'
    return request.cookies.get('scenic_draft')


@router.get('/scenic-selection')
def scenic_selection(request: Request, response: Response):
    owner = scenic_draft_owner(request)
    if not owner:
        owner = uuid4().hex
        response.set_cookie('scenic_draft', owner, httponly=True, samesite='strict', max_age=2592000)
    response.headers['Cache-Control'] = 'no-store'
    with Session(DB_ENGINE) as db:
        spots = db.exec(select(ScenicSpotInfo).join(ScenicDraftStop,
            ScenicDraftStop.spot_id == ScenicSpotInfo.spot_id).where(
            ScenicDraftStop.owner == owner, ScenicSpotInfo.delete == False
        ).order_by(ScenicSpotInfo.spot_id)).all()
        settings = db.get(ScenicDraftSettings, owner)
        order = json.loads(settings.spot_ids) if settings else []
        rank = {sid: index for index, sid in enumerate(order)}
        spots.sort(key=lambda spot: rank.get(spot.spot_id, len(order)+spot.spot_id))
        return [{'id': s.spot_id, 'name': s.spot_name} for s in spots]


@router.put('/scenic-selection')
def select_stop(spot_id: int, request: Request):
    owner = scenic_draft_owner(request)
    if not owner:
        raise HTTPException(409, '请刷新景点清单')
    with Session(DB_ENGINE) as db:
        load_spots(db, [spot_id])
        key = (owner, spot_id)
        if not db.get(ScenicDraftStop, key):
            db.add(ScenicDraftStop(owner=owner, spot_id=key[1]))
            db.commit()


@router.delete('/scenic-selection/{spot_id}')
def remove_stop(spot_id: int, request: Request):
    with Session(DB_ENGINE) as db:
        stop = db.get(ScenicDraftStop, (scenic_draft_owner(request) or '', spot_id))
        if stop:
            db.delete(stop)
            db.commit()


@router.get('/scenic-catalog')
def scenic_catalog():
    with Session(DB_ENGINE) as db:
        spots = db.exec(select(ScenicSpotInfo).where(ScenicSpotInfo.delete == False,
                            ScenicSpotInfo.city.in_(('北京', '北京市')),
                            ScenicSpotInfo.latitude > 39.97, ScenicSpotInfo.latitude < 40.02,
                            ScenicSpotInfo.longitude > 116.24, ScenicSpotInfo.longitude < 116.30)
                        .order_by(ScenicSpotInfo.spot_id)).all()
        return [dict(id=s.spot_id, name=s.spot_name, description=s.description,
                     location=s.location, history=s.history_detail, tip=s.tour_tips,
                     history_detail=s.history_detail, service_facilities=s.service_facilities,
                     photo_tips=s.photo_tips, tour_tips=s.tour_tips, best_season=s.best_season,
                     park='summer-palace' if s.city in ('北京','北京市') and 39.97 < s.latitude < 40.02 and 116.24 < s.longitude < 116.30 else '',
                     latitude=s.latitude, longitude=s.longitude, trigger_radius=s.trigger_radius) for s in spots]


@router.get('/scenic-audio/{spot_id}', summary='播放已保存的完整景点讲解')
def scenic_audio(spot_id: int):
    from pathlib import Path
    from ...web_configs import WEB_CONFIGS
    from ..models.xingyun import XingyunGuideBinding
    from ..modules.scenic_narration import narration_text, narration_revision, voice_identity, recording_file
    with Session(DB_ENGINE) as db:
        spot = db.get(ScenicSpotInfo, spot_id)
        if not spot or spot.delete:
            raise HTTPException(404, '景点不存在')
        record = db.get(ScenicAudio, spot_id)
        binding = db.get(XingyunGuideBinding, record.guide_id) if record else None
        directory = Path(WEB_CONFIGS.SERVER_FILE_ROOT) / WEB_CONFIGS.TOUR_FILE_DIR / 'scenic-audio'
        if (not record or not binding or not recording_file(directory, record)
                or record.revision != narration_revision(narration_text(spot), voice_identity(binding))):
            raise HTTPException(409, '该景点完整讲解尚未生成，请稍后再试')
        return {'url': f'/tour-experience/scenic-audio/{spot_id}/file?v={record.revision}',
                'duration': record.duration, 'source': record.source}


@router.get('/scenic-audio/{spot_id}/file', summary='完整景点音频文件')
def scenic_audio_file(spot_id: int):
    from pathlib import Path
    from fastapi.responses import FileResponse
    from ...web_configs import WEB_CONFIGS
    from ..modules.scenic_narration import recording_file
    scenic_audio(spot_id)  # Recheck deleted/stale/missing recordings on direct requests too.
    with Session(DB_ENGINE) as db:
        record = db.get(ScenicAudio, spot_id)
        directory = Path(WEB_CONFIGS.SERVER_FILE_ROOT) / WEB_CONFIGS.TOUR_FILE_DIR / 'scenic-audio'
        if not record or not recording_file(directory, record):
            raise HTTPException(409, '该景点完整讲解尚未生成，请稍后再试')
        path = directory / record.file_name
        return FileResponse(path, media_type='audio/wav' if path.suffix == '.wav' else 'audio/webm', headers={'Cache-Control': 'no-cache'})


# Anonymous mobile journeys are scoped to the existing HttpOnly draft cookie.
import json
import math
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import UniqueConstraint


class ScenicJourney(SQLModel, table=True):
    journey_id: str = Column(primary_key=True)
    owner: str = Column(index=True)
    spot_ids: str
    mode: str
    guide_id: Optional[int] = None
    tour_id: Optional[int] = None
    ended: bool = False
    created_at: str


class ScenicArrival(SQLModel, table=True):
    __table_args__ = (UniqueConstraint('journey_id', 'spot_id'),)
    arrival_id: str = Column(primary_key=True)
    journey_id: str = Column(index=True)
    spot_id: int
    latitude: float
    longitude: float
    accuracy: float
    distance: float
    created_at: str


class ScenicReview(SQLModel, table=True):
    journey_id: str = Column(primary_key=True)
    quick: int
    satisfaction: int
    tags: str
    recommendation: int
    created_at: str


class ScenicCheckin(SQLModel, table=True):
    checkin_id: str = Column(primary_key=True)
    device_id: str = Column(index=True)
    spot_id: int
    spot_name: str
    image_path: str = ""
    quote: str = ""
    walk_text: str = ""
    duration_text: str = ""
    created_at: str


class CheckinInput(BaseModel):
    spot_id: int
    time: str = ""
    quote: str = ""
    walk: str = ""
    duration: str = ""


class AppReviewInput(BaseModel):
    session_id: int = 0
    quick: int = Field(ge=0, le=2)
    tags: list[str] = Field(default_factory=list, max_length=8)
    recommendation: int = Field(ge=0, le=10)


class JourneyInput(BaseModel):
    spot_ids: list[int] = Field(min_length=1, max_length=20)
    mode: Literal['guide', 'walk']
    guide_id: Optional[int] = None


class ArrivalInput(BaseModel):
    spot_id: int
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    accuracy: float = Field(gt=0, le=100)


class ReviewInput(BaseModel):
    quick: int = Field(ge=0, le=2)
    satisfaction: int = Field(ge=0, le=2)
    tags: list[str] = Field(max_length=6)
    recommendation: int = Field(ge=0, le=10)


REVIEW_TAGS = {'讲解清楚', '路线方便', '风景优美', '内容有趣', '定位不准', '讲解需改进', '步行较累'}


def owned_journey(db, jid, request):
    journey = db.get(ScenicJourney, jid)
    if not journey or journey.owner != request.cookies.get('scenic_draft'):
        raise HTTPException(404, '游览记录不存在')
    return journey


def distance_m(lat, lng, target_lat, target_lng):
    a, b = math.radians(lat), math.radians(target_lat)
    dlat, dlng = b-a, math.radians(target_lng-lng)
    value = math.sin(dlat/2)**2 + math.cos(a)*math.cos(b)*math.sin(dlng/2)**2
    return 6371000 * 2 * math.asin(min(1, math.sqrt(value)))


def owner_key(request: Request, device: str = '') -> str:
    auth = request.headers.get('authorization', '')
    if auth.lower().startswith('bearer '):
        try:
            from .users import get_current_user_info
            uid = get_current_user_info(auth.split(' ', 1)[1])
            if uid: return f'user:{uid}'
        except Exception:
            pass
    return (device or request.cookies.get('scenic_draft') or '').strip()


@router.post('/checkins')
def add_checkin(body: CheckinInput, request: Request, x_device_id: str = Header(default='')):
    device = owner_key(request, x_device_id)
    if not device: raise HTTPException(422, '缺少设备标识')
    with Session(DB_ENGINE) as db:
        spot = db.get(ScenicSpotInfo, body.spot_id)
        if not spot or spot.delete: raise HTTPException(404, '景点不存在')
        exists = db.exec(select(ScenicCheckin).where(ScenicCheckin.device_id == device,
            ScenicCheckin.spot_id == body.spot_id)).first()
        if exists:
            return {'id': exists.checkin_id, 'spot_name': exists.spot_name, 'time': exists.created_at, 'duplicate': True}
        row = ScenicCheckin(checkin_id=uuid4().hex, device_id=device, spot_id=spot.spot_id,
            spot_name=spot.spot_name, image_path=spot.image_path or '',
            quote=body.quote, walk_text=body.walk, duration_text=body.duration,
            created_at=body.time or datetime.now(timezone.utc).isoformat())
        db.add(row); db.commit()
        return {'id': row.checkin_id, 'spot_name': row.spot_name, 'image_path': row.image_path,
                'quote': row.quote, 'walk': row.walk_text, 'duration': row.duration_text,
                'time': row.created_at, 'duplicate': False}


@router.get('/checkins')
def list_checkins(request: Request, x_device_id: str = Header(default='')):
    device = owner_key(request, x_device_id)
    if not device: return []
    with Session(DB_ENGINE) as db:
        rows = db.exec(select(ScenicCheckin).where(ScenicCheckin.device_id == device)
                       .order_by(ScenicCheckin.created_at.desc())).all()
        return [{'id': r.checkin_id, 'spot_id': r.spot_id, 'spot_name': r.spot_name,
                 'image_path': r.image_path, 'quote': r.quote, 'walk': r.walk_text,
                 'duration': r.duration_text, 'time': r.created_at} for r in rows]


@router.delete('/checkins/{checkin_id}')
def remove_checkin(checkin_id: str, request: Request, x_device_id: str = Header(default='')):
    owner = owner_key(request, x_device_id)
    with Session(DB_ENGINE) as db:
        row = db.get(ScenicCheckin, checkin_id)
        if not row or row.device_id != owner: raise HTTPException(404, '打卡记录不存在')
        db.delete(row); db.commit()
    return {'ok': True}


@router.post('/reviews/app')
def app_review(body: AppReviewInput, request: Request, x_device_id: str = Header(default='')):
    device = owner_key(request, x_device_id) or 'app'
    with Session(DB_ENGINE) as db:
        key = f'app:{device}:{body.session_id}'
        row = db.get(ScenicReview, key)
        if not row:
            row = ScenicReview(journey_id=key, quick=body.quick, satisfaction=body.quick,
                tags=json.dumps(body.tags, ensure_ascii=False), recommendation=body.recommendation,
                created_at=datetime.now(timezone.utc).isoformat())
        else:
            row.quick=body.quick; row.satisfaction=body.quick; row.tags=json.dumps(body.tags, ensure_ascii=False)
            row.recommendation=body.recommendation
        db.add(row); db.commit()
    return {'ok': True}


@router.get('/companions')
async def companions():
    from .tour_chat import get_visitor_guides
    result = await get_visitor_guides()
    return result['data']['guide_list']


@router.post('/journeys')
async def create_journey(body: JourneyInput, request: Request):
    owner = request.cookies.get('scenic_draft')
    if not owner: raise HTTPException(409, '请先重新加载景点清单')
    tour_id, access = None, ''
    with Session(DB_ENGINE) as db:
        load_spots(db, body.spot_ids)
    with Session(DB_ENGINE) as db:
        settings = db.get(ScenicDraftSettings, owner)
        avoid_steps = bool(settings and (settings.avoid_steps or settings.elderly or settings.children))
    if body.mode == 'guide':
        if not body.guide_id: raise HTTPException(422, '请选择伴游')
        from .tour_chat import visitor_create_session
        result = await visitor_create_session(name='伴游讲解', guide_id=body.guide_id,
            spot_ids=json.dumps(body.spot_ids), planning=json.dumps({'pace':'relaxed' if avoid_steps else 'standard',
                'avoid_steps':avoid_steps,'start_area':settings.start_area if settings else 'auto',
                'end_area':settings.end_area if settings else 'auto'}), authorization=None)
        if not result['success']: raise HTTPException(422, result['message'])
        tour_id = result['data']['session_id']
        access = result['data']['avatar_access_token']
    journey = ScenicJourney(journey_id=uuid4().hex, owner=owner,
        spot_ids=json.dumps(body.spot_ids), mode=body.mode, guide_id=body.guide_id,
        tour_id=tour_id, created_at=datetime.now(timezone.utc).isoformat())
    with Session(DB_ENGINE) as db:
        db.add(journey)
        db.commit()
        db.refresh(journey)
    return {'id': journey.journey_id, 'tour_id': tour_id, 'access_token': access}


@router.get('/journeys/{jid}')
def journey_detail(jid: str, request: Request):
    with Session(DB_ENGINE) as db:
        journey = owned_journey(db, jid, request)
        spots = load_spots(db, json.loads(journey.spot_ids))
        arrivals = db.exec(select(ScenicArrival).where(ScenicArrival.journey_id == jid)).all()
        review = db.get(ScenicReview, jid)
        settings = db.get(ScenicDraftSettings, journey.owner)
        return {'id': jid, 'mode': journey.mode, 'guide_id': journey.guide_id,
            'tour_id': journey.tour_id, 'ended': journey.ended,
            'avoid_steps': bool(settings and (settings.avoid_steps or settings.elderly or settings.children)),
            'spots': spots, 'arrivals': [a.model_dump() for a in arrivals],
            'review': review.model_dump() if review else None}


@router.post('/journeys/{jid}/arrivals')
def confirm_arrival(jid: str, body: ArrivalInput, request: Request):
    with Session(DB_ENGINE) as db:
        journey = owned_journey(db, jid, request)
        if journey.ended: raise HTTPException(409, '游览已结束')
        if body.spot_id not in json.loads(journey.spot_ids): raise HTTPException(422, '景点不在路线中')
        spot = db.get(ScenicSpotInfo, body.spot_id)
        if not spot or spot.delete or not spot.latitude or not spot.longitude:
            raise HTTPException(422, '景点尚未配置定位')
        distance = distance_m(body.latitude, body.longitude, spot.latitude, spot.longitude)
        if distance > max(50, min(spot.trigger_radius, 150)):
            raise HTTPException(422, '距离景点较远，请到达附近后打卡')
        existing = db.exec(select(ScenicArrival).where(
            ScenicArrival.journey_id == jid, ScenicArrival.spot_id == body.spot_id)).first()
        if existing: return existing.model_dump()
        arrival = ScenicArrival(arrival_id=uuid4().hex, journey_id=jid, spot_id=body.spot_id,
            latitude=body.latitude, longitude=body.longitude, accuracy=body.accuracy,
            distance=round(distance, 1), created_at=datetime.now(timezone.utc).isoformat())
        db.add(arrival)
        from sqlalchemy.exc import IntegrityError
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            arrival = db.exec(select(ScenicArrival).where(
                ScenicArrival.journey_id == jid, ScenicArrival.spot_id == body.spot_id)).one()
        db.refresh(arrival)
        return arrival.model_dump()


@router.put('/journeys/{jid}/end')
async def end_journey(jid: str, request: Request):
    with Session(DB_ENGINE) as db:
        journey = owned_journey(db, jid, request)
        tour_id = journey.tour_id
        if tour_id:
            from ..database.tour_session_db import end_tour_session
            await end_tour_session(tour_id)
        journey.ended = True
        db.add(journey)
        db.commit()
    return {'ended': True}


@router.put('/journeys/{jid}/review')
def save_journey_review(jid: str, body: ReviewInput, request: Request):
    if not set(body.tags).issubset(REVIEW_TAGS): raise HTTPException(422, '评价标签无效')
    with Session(DB_ENGINE) as db:
        journey = owned_journey(db, jid, request)
        if not journey.ended: raise HTTPException(409, '请先结束游览')
        review = db.get(ScenicReview, jid) or ScenicReview(journey_id=jid, quick=body.quick,
            satisfaction=body.satisfaction, tags='[]', recommendation=body.recommendation, created_at='')
        review.quick, review.satisfaction = body.quick, body.satisfaction
        review.tags = json.dumps(list(dict.fromkeys(body.tags)), ensure_ascii=False)
        review.recommendation = body.recommendation
        review.created_at = datetime.now(timezone.utc).isoformat()
        db.add(review)
        db.commit()
    return {'saved': True}


class ScenicDraftSettings(SQLModel, table=True):
    owner: str = Column(primary_key=True)
    spot_ids: str = '[]'
    elderly: bool = False
    children: bool = False
    avoid_steps: bool = False
    start_area: str = 'auto'
    end_area: str = 'auto'


class DraftSettingsInput(BaseModel):
    spot_ids: list[int] | None = Field(default=None, max_length=20)
    elderly: bool | None = None
    children: bool | None = None
    avoid_steps: bool | None = None
    start_area: Literal['auto','east','north','south'] | None = None
    end_area: Literal['auto','east','north','south'] | None = None


def draft_settings_data(settings):
    return dict(spot_ids=json.loads(settings.spot_ids), elderly=settings.elderly,
                children=settings.children, avoid_steps=settings.avoid_steps or settings.elderly or settings.children,
                few_steps=settings.avoid_steps, start_area=settings.start_area, end_area=settings.end_area)


@router.get('/scenic-settings')
def get_draft_settings(request: Request):
    owner = scenic_draft_owner(request)
    if not owner: raise HTTPException(409, '请先加载景点清单')
    with Session(DB_ENGINE) as db:
        settings = db.get(ScenicDraftSettings, owner) or ScenicDraftSettings(owner=owner)
        return draft_settings_data(settings)


@router.put('/scenic-settings')
def save_draft_settings(body: DraftSettingsInput, request: Request):
    owner = scenic_draft_owner(request)
    if not owner: raise HTTPException(409, '请先加载景点清单')
    with Session(DB_ENGINE) as db:
        # Serialize concurrent edits, including the first settings save.
        from sqlalchemy import text
        db.execute(text('SELECT pg_advisory_xact_lock(hashtext(:owner))'), {'owner': owner})
        settings = db.get(ScenicDraftSettings, owner) or ScenicDraftSettings(owner=owner)
        if body.spot_ids is not None:
            actual = db.exec(select(ScenicDraftStop.spot_id).where(ScenicDraftStop.owner == owner)).all()
            if len(body.spot_ids) != len(set(body.spot_ids)) or set(body.spot_ids) != set(actual):
                raise HTTPException(409, '景点清单已变更，请刷新后重排')
            settings.spot_ids = json.dumps(body.spot_ids)
        if body.elderly is not None: settings.elderly = body.elderly
        if body.children is not None: settings.children = body.children
        if body.avoid_steps is not None: settings.avoid_steps = body.avoid_steps
        if body.start_area is not None: settings.start_area = body.start_area
        if body.end_area is not None: settings.end_area = body.end_area
        db.add(settings)
        db.commit()
        db.refresh(settings)
        return draft_settings_data(settings)


class ScenicParkServices(SQLModel, table=True):
    park_id: str = Column(primary_key=True)
    payload: str


@router.get('/park-services/{park_id}')
def park_services(park_id: str):
    with Session(DB_ENGINE) as db:
        row = db.get(ScenicParkServices, park_id)
        if not row: raise HTTPException(404, '该景区设施资料尚未收录')
        return json.loads(row.payload)
