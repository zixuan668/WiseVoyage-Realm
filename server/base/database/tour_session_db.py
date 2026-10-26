#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    :   tour_session_db.py
@Time    :   2026/06/10
@Project :   景区导览AI数字人
@Desc    :   导览会话数据表读写
"""

from datetime import datetime
from typing import List

from loguru import logger
from sqlmodel import Session, and_, select

from ..models.tour_models import (
    DigitalGuideInfo,
    ScenicSpotInfo,
    SpotVisitRecord,
    TourRoute,
    TourSessionInfo,
    TourSessionStatus,
    VisitorInteraction,
)
from ..modules.guide_identity import SHOWCASE_GUIDE_NAME, resolve_guide_voice
from .digital_guide_db import _asset_url
from .init_db import DB_ENGINE


def _answer_metadata(raw: str) -> dict:
    import json
    try:
        value=json.loads(raw or "{}")
        return value if isinstance(value,dict) else {}
    except (ValueError,TypeError):
        return {}


def _session_route_spots(session: Session, tour_session, route_info):
    """Use the saved itinerary for visitor tours; legacy tours use route order."""
    preferences = _answer_metadata(tour_session.visitor_preferences)
    if "spot_ids" in preferences:
        ids = preferences["spot_ids"]
        if not isinstance(ids, list) or any(type(i) is not int for i in ids):
            return [], "路线数据格式错误，请重新规划行程"
        spots = [session.get(ScenicSpotInfo, sid) for sid in ids]
    else:
        spots = [rs.spot_info for rs in sorted(
            route_info.route_spots if route_info else [], key=lambda rs: rs.spot_order
        )]
    if not spots:
        return [], "本次导览没有景点，请重新规划行程"
    if any(spot is None or spot.delete for spot in spots):
        return [], "路线中的景点已不可用，请重新规划行程"
    return spots, ""


def _route_spot_data(spot):
    if spot is None:
        return None
    from ...web_configs import API_CONFIG
    fields = ("spot_id", "spot_name", "category", "description", "history_detail",
              "location", "best_season", "visit_duration", "photo_tips",
              "service_facilities", "tour_tips", "latitude", "longitude", "city")
    result = {key: getattr(spot, key, None) for key in fields}
    result["image_path"] = _asset_url(spot.image_path)
    return result


async def create_tour_session(
    name: str,
    route_id: int,
    guide_id: int,
    user_id: int,
    visitor_preferences: str = "",
) -> TourSessionInfo:
    """创建新的导览会话

    Args:
        name: 会话名称
        route_id: 路线 ID
        guide_id: 导游 ID
        user_id: 用户 ID
        visitor_preferences: 游客偏好 JSON

    Returns:
        TourSessionInfo: 创建的会话
    """
    with Session(DB_ENGINE) as session:
        # 用户所选身份不可被静默替换；下架或删除后拒绝创建。
        selected_guide = session.exec(
            select(DigitalGuideInfo).where(
                and_(DigitalGuideInfo.guide_id == guide_id, DigitalGuideInfo.delete == False)
            )
        ).first()
        from ..modules.xingyun_access import selectable
        from fastapi import HTTPException
        if not selectable(session, selected_guide):
            raise HTTPException(409, "所选数字导游已下架或不可用，请重新选择")

        # 创建会话状态
        status = TourSessionStatus(live_status=0)
        session.add(status)
        session.commit()
        session.refresh(status)

        # 创建会话
        tour_session = TourSessionInfo(
            name=name,
            route_id=route_id,
            guide_id=guide_id,
            user_id=user_id,
            visitor_preferences=visitor_preferences,
            status_id=status.status_id,
        )
        session.add(tour_session)
        session.commit()
        session.refresh(tour_session)

    return tour_session


async def get_db_tour_sessions(
    user_id: int,
    current_page: int = -1,
    page_size: int = 10,
) -> tuple:
    """查询导览会话列表"""
    from sqlalchemy import func

    conditions = [TourSessionInfo.delete == False]
    if user_id > 0:
        conditions.append(TourSessionInfo.user_id == user_id)
    query_condition = and_(*conditions)

    with Session(DB_ENGINE) as session:
        total_count = session.scalar(select(func.count(TourSessionInfo.session_id)).where(query_condition))

        if current_page < 0:
            sessions = session.exec(
                select(TourSessionInfo).where(query_condition).order_by(TourSessionInfo.session_id.desc())
            ).all()
        else:
            offset_idx = (current_page - 1) * page_size
            sessions = session.exec(
                select(TourSessionInfo)
                .where(query_condition)
                .offset(offset_idx)
                .limit(page_size)
                .order_by(TourSessionInfo.session_id.desc())
            ).all()

    if sessions is None:
        sessions = []

    return sessions, total_count


async def start_tour_session(session_id: int) -> bool:
    """开始导览会话

    Args:
        session_id: 会话 ID

    Returns:
        bool: 是否成功
    """
    try:
        with Session(DB_ENGINE) as session:
            tour_session = session.exec(
                select(TourSessionInfo).where(TourSessionInfo.session_id == session_id)
            ).one()

            if tour_session and tour_session.status:
                tour_session.status.live_status = 1
                tour_session.status.start_time = datetime.now()
                session.add(tour_session.status)
                session.commit()
                return True
        return False
    except Exception as e:
        logger.error(f"Start session failed: {e}")
        return False


async def end_tour_session(session_id: int) -> bool:
    """结束导览会话

    Args:
        session_id: 会话 ID

    Returns:
        bool: 是否成功
    """
    try:
        with Session(DB_ENGINE) as session:
            tour_session = session.exec(
                select(TourSessionInfo).where(TourSessionInfo.session_id == session_id)
            ).one()

            if tour_session and tour_session.status:
                tour_session.status.live_status = 2
                tour_session.status.end_time = datetime.now()
                session.add(tour_session.status)
                session.commit()
                return True
        return False
    except Exception as e:
        logger.error(f"End session failed: {e}")
        return False


async def get_session_live_info(session_id: int):
    """获取导览会话实时信息（包含对话历史、当前景点、视频）"""
    from ...web_configs import API_CONFIG

    with Session(DB_ENGINE) as session:
        tour_session = session.exec(
            select(TourSessionInfo).where(TourSessionInfo.session_id == session_id)
        ).first()

        if not tour_session:
            return None

        # 获取导游信息
        guide_info = None
        if tour_session.guide_id:
            guide_info = session.exec(
                select(DigitalGuideInfo).where(
                    and_(
                        DigitalGuideInfo.guide_id == tour_session.guide_id,
                    )
                )
            ).first()

        # 获取路线信息
        route_info = None
        if tour_session.route_id:
            route_info = session.exec(
                select(TourRoute).where(TourRoute.route_id == tour_session.route_id)
            ).first()

        # 获取对话历史
        conversations = session.exec(
            select(VisitorInteraction)
            .where(VisitorInteraction.session_id == session_id)
            .order_by(VisitorInteraction.send_time)
        ).all()

        conversation_list = []
        for msg in (conversations or []):
            conversation_list.append({
                "role": msg.role,
                "userId": msg.user_id,
                "userName": "游客" if msg.role == "user" else (guide_info.name if guide_info else "导游"),
                "avatar": guide_info.avatar if guide_info and msg.role == "guide" else "",
                "message": msg.message,
                "aiMeta": _answer_metadata(msg.answer_metadata),
                "send_time": str(msg.send_time) if msg.send_time else "",
            })

        # 获取当前景点信息
        current_spot = None
        next_spot = None
        current_spot_index = tour_session.status.current_spot_index if tour_session.status else 0
        spots, route_error = _session_route_spots(session, tour_session, route_info)
        if spots and not 0 <= current_spot_index < len(spots):
            route_error = "路线进度异常，请重新规划行程"
        if not route_error:
            current_spot = spots[current_spot_index]
            if current_spot_index + 1 < len(spots):
                next_spot = spots[current_spot_index + 1]

        guide_voice_style = resolve_guide_voice(
            guide_info.voice_style if guide_info else "female_wenrou",
        )

        from ..modules.route_presentation import route_overview
        preferences = _answer_metadata(tour_session.visitor_preferences)
        plan = preferences.get('last_replan') or preferences.get('planning') or {}
        if not isinstance(plan,dict): plan={}
        station_origin = preferences.get('station_origin') if preferences.get('station_plan') else None
        station_end = station_origin if plan.get('end_area') == 'return' else None
        overview = route_overview([s.model_dump() for s in spots], plan.get('pace', 'standard'),
            end_area=plan.get('end_area', 'auto'), avoid_steps=plan.get('avoid_steps', plan.get('pace') == 'relaxed'),
            start_anchor=station_origin, end_anchor=station_end)

        result = {
            "session_id": tour_session.session_id,
            "name": tour_session.name,
            "visitor_preferences": tour_session.visitor_preferences,
            "guide_info": {
                "guide_id": guide_info.guide_id if guide_info else 0,
                "render_mode": guide_info.render_mode if guide_info else "",
                "is_enabled": bool(guide_info and guide_info.is_enabled and not guide_info.delete),
                "name": guide_info.name if guide_info else "",
                "name_en": (getattr(guide_info, "name_en", "") or "") if guide_info else "",
                "character": guide_info.character if guide_info else "",
                "character_en": (getattr(guide_info, "character_en", "") or "") if guide_info else "",
                "avatar": _asset_url(guide_info.avatar) if guide_info and guide_info.avatar else "",
                "poster_image": _asset_url(guide_info.poster_image) if guide_info and guide_info.poster_image else "",
                "base_mp4_path": _asset_url(guide_info.base_mp4_path) if guide_info and guide_info.base_mp4_path else "",
                "voice_style": guide_voice_style,
                "voice_speed": guide_info.voice_speed if guide_info else 1.0,
            } if guide_info else None,
            "route_info": {
                "route_id": route_info.route_id if route_info else 0,
                "name": route_info.name if route_info else "",
                "theme": route_info.theme if route_info else "",
                "estimated_time": overview['total_minutes'],
            } if route_info else None,
            "current_spot_index": current_spot_index,
            "current_streamer_video": API_CONFIG.REQUEST_FILES_URL + tour_session.status.streaming_video_path if tour_session.status and tour_session.status.streaming_video_path else "",
            "live_status": tour_session.status.live_status if tour_session.status else 0,
            "start_time": str(tour_session.status.start_time) if tour_session.status and tour_session.status.start_time else "",
            "final_spot": False,  # 是否最后一个景点
            "conversation": conversation_list,
        }

        result["current_spot_info"] = _route_spot_data(current_spot)
        result["next_spot_info"] = _route_spot_data(next_spot)
        result["route_spots"] = [_route_spot_data(spot) for spot in spots]
        result["route_overview"] = overview
        result["remaining_route_overview"] = overview if station_origin and current_spot_index == 0 else route_overview([s.model_dump() for s in spots[current_spot_index:]],
            plan.get('pace', 'standard'), include_first_visit=False, end_area=plan.get('end_area', 'auto'),
            avoid_steps=plan.get('avoid_steps', plan.get('pace') == 'relaxed'), reserve=plan.get('reserve_minutes', plan.get('queue_reserve_minutes', 0)), end_anchor=station_end)
        result["route_error"] = route_error
        result["final_spot"] = bool(spots) and current_spot_index >= len(spots) - 1

        return result


async def next_spot_in_session(session_id: int) -> bool:
    """切换到下一个景点

    Args:
        session_id: 会话 ID

    Returns:
        bool: 是否成功
    """
    try:
        with Session(DB_ENGINE) as session:
            tour_session = session.exec(
                select(TourSessionInfo).where(TourSessionInfo.session_id == session_id).with_for_update()
            ).one()

            if tour_session and tour_session.status:
                if tour_session.status.live_status == 2: return False
                session.exec(select(TourSessionStatus).where(TourSessionStatus.status_id == tour_session.status_id).with_for_update()).one()
                route_info = session.get(TourRoute, tour_session.route_id) if tour_session.route_id else None
                spots, route_error = _session_route_spots(session, tour_session, route_info)
                index = tour_session.status.current_spot_index
                if route_error or not 0 <= index < len(spots) - 1:
                    return False
                tour_session.status.current_spot_index += 1
                session.add(tour_session.status)
                session.commit()
                return True
        return False
    except Exception as e:
        logger.error(f"Next spot failed: {e}")
        return False


async def save_visitor_message(session_id: int, user_id: int, guide_id: int, role: str, message: str) -> VisitorInteraction:
    """保存游客交互消息

    Args:
        session_id: 会话 ID
        user_id: 用户 ID
        guide_id: 导游 ID
        role: 角色
        message: 消息内容

    Returns:
        VisitorInteraction: 创建的消息记录
    """
    with Session(DB_ENGINE) as session:
        interaction = VisitorInteraction(
            session_id=session_id,
            user_id=user_id,
            guide_id=guide_id,
            role=role,
            message=message,
            send_time=datetime.now(),
        )
        session.add(interaction)
        session.commit()
        session.refresh(interaction)
    return interaction


async def get_conversation_history(session_id: int) -> List[dict]:
    """获取会话对话历史

    Args:
        session_id: 会话 ID

    Returns:
        List[dict]: 对话历史
    """
    with Session(DB_ENGINE) as session:
        messages = session.exec(
            select(VisitorInteraction)
            .where(VisitorInteraction.session_id == session_id)
            .order_by(VisitorInteraction.send_time)
        ).all()

    if messages is None:
        return []

    return [
        {
            "role": msg.role,
            "message": msg.message,
            "aiMeta": _answer_metadata(msg.answer_metadata),
            "send_time": str(msg.send_time) if msg.send_time else "",
        }
        for msg in messages
    ]


async def delete_tour_session(session_id: int) -> bool:
    """软删除导览会话

    Args:
        session_id: 会话 ID

    Returns:
        bool: 是否成功
    """
    try:
        with Session(DB_ENGINE) as session:
            tour_session = session.exec(
                select(TourSessionInfo).where(TourSessionInfo.session_id == session_id)
            ).one()
            if tour_session:
                tour_session.delete = True
                session.add(tour_session)
                session.commit()
                return True
        return False
    except Exception as e:
        logger.error(f"Delete session failed: {e}")
        return False


async def update_session_video_path(status_id: int, video_path: str) -> bool:
    """更新会话当前视频路径

    Args:
        status_id: 状态 ID
        video_path: 视频路径

    Returns:
        bool: 是否成功
    """
    try:
        with Session(DB_ENGINE) as session:
            status = session.exec(
                select(TourSessionStatus).where(TourSessionStatus.status_id == status_id)
            ).one()
            if status:
                status.streaming_video_path = video_path
                session.add(status)
                session.commit()
                return True
        return False
    except Exception:
        return False


def get_dialogue_context(session_id: int) -> dict:
    import json
    with Session(DB_ENGINE) as db:
        tour = db.get(TourSessionInfo, session_id)
        try:
            value = json.loads(tour.dialogue_context or "{}") if tour else {}
            return value if isinstance(value, dict) else {}
        except (ValueError, TypeError):
            return {}


def save_dialogue_context(session_id: int, memory: dict, message_id: int, metadata: dict):
    import json
    with Session(DB_ENGINE) as db:
        tour = db.get(TourSessionInfo, session_id)
        message = db.get(VisitorInteraction, message_id)
        if tour:
            tour.dialogue_context = json.dumps(memory, ensure_ascii=False)
            db.add(tour)
        if message:
            message.answer_metadata = json.dumps(metadata, ensure_ascii=False)
            db.add(message)
        db.commit()
