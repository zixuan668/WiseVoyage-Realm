"""Shared route geometry and order calculations for the station, admin and App."""
from typing import Literal
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from ..database.init_db import DB_ENGINE
from ..models.tour_models import ScenicSpotInfo
from ..modules.route_city import route_city
from ..modules.route_presentation import route_overview
from ..utils import make_return_data, ResultCode

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
