#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    :   tour_route_db.py
@Time    :   2026/06/10
@Project :   景区导览AI数字人
@Desc    :   游览路线数据表读写
"""

from typing import List, Tuple

from loguru import logger
from sqlalchemy import func
from sqlmodel import Session, and_, select

from ..models.tour_models import ScenicSpotInfo, TourRoute, TourRouteCreate, TourRouteSpot
from .init_db import DB_ENGINE
from ..modules.route_city import route_city


def validate_route_city(session,spot_ids,user_id):
    spots=[session.get(ScenicSpotInfo,sid) for sid in dict.fromkeys(spot_ids)]
    if any(not s or s.delete or s.user_id!=user_id for s in spots):
        raise ValueError('路线包含不存在或无权使用的景点')
    return route_city(spots)


async def get_db_tour_routes(
    user_id: int,
    current_page: int = -1,
    page_size: int = 10,
    theme: str | None = None,
) -> Tuple[List[TourRoute], int]:
    """查询游览路线列表

    Args:
        user_id: 用户 ID
        current_page: 页数
        page_size: 每页大小
        theme: 按主题筛选

    Returns:
        List[TourRoute]: 路线列表
        int: 总数
    """
    query_condition = and_(TourRoute.user_id == user_id, TourRoute.delete == False)

    if theme is not None:
        query_condition = and_(query_condition, TourRoute.theme == theme)

    with Session(DB_ENGINE) as session:
        total_count = session.scalar(select(func.count(TourRoute.route_id)).where(query_condition))

        if current_page < 0:
            routes = session.exec(
                select(TourRoute).where(query_condition).order_by(TourRoute.route_id)
            ).all()
        else:
            offset_idx = (current_page - 1) * page_size
            routes = session.exec(
                select(TourRoute)
                .where(query_condition)
                .offset(offset_idx)
                .limit(page_size)
                .order_by(TourRoute.route_id)
            ).all()

    if routes is None:
        routes = []

    return routes, total_count


async def get_db_tour_route_detail(route_id: int, user_id: int) -> TourRoute | None:
    """获取路线详情（含景点列表）

    Args:
        route_id: 路线 ID
        user_id: 用户 ID

    Returns:
        TourRoute | None
    """
    with Session(DB_ENGINE) as session:
        route = session.exec(
            select(TourRoute).where(
                and_(TourRoute.route_id == route_id, TourRoute.user_id == user_id, TourRoute.delete == False)
            )
        ).first()
    return route


async def create_tour_route(new_route: TourRouteCreate, user_id: int) -> TourRoute:
    """创建新的游览路线

    Args:
        new_route: 路线创建请求
        user_id: 用户 ID

    Returns:
        TourRoute: 创建的路线
    """
    with Session(DB_ENGINE) as session:
        city=validate_route_city(session,new_route.spot_ids,user_id)
        route = TourRoute(
            name=new_route.name,
            theme=new_route.theme,
            estimated_time_minutes=new_route.estimated_time_minutes,
            description=new_route.description,
            user_id=user_id,
            city=city,
        )
        session.add(route)
        session.flush()

        # 添加路线-景点关联
        for idx, spot_id in enumerate(new_route.spot_ids):
            route_spot = TourRouteSpot(
                route_id=route.route_id,
                spot_id=spot_id,
                spot_order=idx,
            )
            session.add(route_spot)

        session.commit()
        session.refresh(route)

    return route


async def update_tour_route(route_id: int, new_route: TourRouteCreate, user_id: int) -> bool:
    """更新游览路线

    Args:
        route_id: 路线 ID
        new_route: 新路线信息
        user_id: 用户 ID

    Returns:
        bool: 是否成功
    """
    try:
        with Session(DB_ENGINE) as session:
            route = session.exec(
                select(TourRoute).where(
                    and_(TourRoute.route_id == route_id, TourRoute.user_id == user_id)
                )
            ).one()

            if route is None:
                return False

            route.city=validate_route_city(session,new_route.spot_ids,user_id)

            route.name = new_route.name
            route.theme = new_route.theme
            route.estimated_time_minutes = new_route.estimated_time_minutes
            route.description = new_route.description
            session.add(route)

            # 删除旧的关联
            old_spots = session.exec(
                select(TourRouteSpot).where(TourRouteSpot.route_id == route_id)
            ).all()
            for spot in old_spots:
                session.delete(spot)

            # 添加新的关联
            for idx, spot_id in enumerate(new_route.spot_ids):
                route_spot = TourRouteSpot(
                    route_id=route_id,
                    spot_id=spot_id,
                    spot_order=idx,
                )
                session.add(route_spot)

            session.commit()
        return True
    except ValueError:
        raise
    except Exception as e:
        logger.error(f"Update tour route failed: {e}")
        return False


async def delete_tour_route(route_id: int, user_id: int) -> bool:
    """软删除游览路线

    Args:
        route_id: 路线 ID
        user_id: 用户 ID

    Returns:
        bool: 是否成功
    """
    try:
        with Session(DB_ENGINE) as session:
            route = session.exec(
                select(TourRoute).where(
                    and_(TourRoute.route_id == route_id, TourRoute.user_id == user_id)
                )
            ).one()
            if route:
                route.delete = True
                session.add(route)
                session.commit()
                return True
        return False
    except Exception:
        return False


async def get_route_spots(route_id: int) -> List[ScenicSpotInfo]:
    """获取路线中的所有景点（按顺序）

    Args:
        route_id: 路线 ID

    Returns:
        List[ScenicSpotInfo]: 景点列表
    """
    with Session(DB_ENGINE) as session:
        route_spots = session.exec(
            select(TourRouteSpot)
            .where(TourRouteSpot.route_id == route_id)
            .order_by(TourRouteSpot.spot_order)
        ).all()

        spots = []
        for rs in route_spots:
            spot = session.exec(
                select(ScenicSpotInfo).where(ScenicSpotInfo.spot_id == rs.spot_id)
            ).first()
            if spot:
                spots.append(spot)

    return spots
