from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlmodel import Session, select

from ..database.init_db import DB_ENGINE
from datetime import datetime, timezone
from ..models.spot_favorite import SpotFavorite, SpotView
from ..models.tour_models import ScenicSpotInfo
from ..utils import ResultCode, make_return_data
from .users import get_current_user_info

router = APIRouter(prefix="/spot-favorites", tags=["spot-favorites"])


@router.get("/history")
def list_history(user_id: int = Depends(get_current_user_info)):
    with Session(DB_ENGINE) as session:
        rows = session.exec(select(ScenicSpotInfo, SpotView.viewed_at).join(SpotView)
            .where(SpotView.user_id == user_id, ScenicSpotInfo.delete == False)
            .order_by(SpotView.viewed_at.desc()).limit(50)).all()
        return make_return_data(True, ResultCode.SUCCESS, "成功", {"spot_list": [
            {**spot.model_dump(), "viewTime": (viewed_at.replace(tzinfo=timezone.utc) if viewed_at.tzinfo is None else viewed_at).isoformat()} for spot, viewed_at in rows
        ]})


@router.put("/history/{spot_id}")
def record_view(spot_id: int, user_id: int = Depends(get_current_user_info)):
    with Session(DB_ENGINE) as session:
        spot = session.get(ScenicSpotInfo, spot_id)
        if not spot or spot.delete:
            raise HTTPException(404, "景点不存在")
        record = session.get(SpotView, (user_id, spot_id)) or SpotView(user_id=user_id, spot_id=spot_id)
        record.viewed_at = datetime.now(timezone.utc)
        session.add(record)
        session.commit()
        return make_return_data(True, ResultCode.SUCCESS, "成功", {"spot_id": spot_id})


@router.get("")
def list_favorites(user_id: int = Depends(get_current_user_info)):
    with Session(DB_ENGINE) as session:
        spots = session.exec(
            select(ScenicSpotInfo).join(SpotFavorite)
            .where(SpotFavorite.user_id == user_id, ScenicSpotInfo.delete == False)
            .order_by(SpotFavorite.created_at.desc())
        ).all()
        return make_return_data(True, ResultCode.SUCCESS, "成功", {"spot_list": spots})


@router.get("/counts")
def favorite_counts():
    with Session(DB_ENGINE) as session:
        rows = session.exec(select(SpotFavorite.spot_id, func.count()).group_by(SpotFavorite.spot_id)).all()
        return make_return_data(True, ResultCode.SUCCESS, "成功", dict(rows))


@router.put("/{spot_id}")
def add_favorite(spot_id: int, user_id: int = Depends(get_current_user_info)):
    with Session(DB_ENGINE) as session:
        spot = session.get(ScenicSpotInfo, spot_id)
        if not spot or spot.delete:
            raise HTTPException(404, "景点不存在")
        if session.get(SpotFavorite, (user_id, spot_id)) is None:
            session.add(SpotFavorite(user_id=user_id, spot_id=spot_id))
            session.commit()
        return make_return_data(True, ResultCode.SUCCESS, "已收藏", {"spot_id": spot_id, "favorited": True})


@router.delete("/{spot_id}")
def remove_favorite(spot_id: int, user_id: int = Depends(get_current_user_info)):
    with Session(DB_ENGINE) as session:
        favorite = session.get(SpotFavorite, (user_id, spot_id))
        if favorite is not None:
            session.delete(favorite)
            session.commit()
        return make_return_data(True, ResultCode.SUCCESS, "已取消收藏", {"spot_id": spot_id, "favorited": False})
