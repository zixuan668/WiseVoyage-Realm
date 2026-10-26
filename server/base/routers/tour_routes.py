#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    :   tour_routes.py
@Time    :   2026/06/10
@Project :   景区导览AI数字人
@Desc    :   游览路线管理接口
"""

from fastapi import APIRouter, Depends
from loguru import logger

from ..database.scenic_spot_db import get_db_scenic_spot_info
from ..database.tour_route_db import (
    create_tour_route,
    delete_tour_route,
    get_db_tour_route_detail,
    get_db_tour_routes,
    get_route_spots,
    update_tour_route,
)
from ..models.tour_models import PreferenceItem, RouteRecommendRequest, TourRouteCreate
from ..modules.route_recommender import parse_preferences_from_message, recommend_route
from ..utils import ResultCode, make_return_data
from .users import get_current_user_info

router = APIRouter(
    prefix="/tour-routes",
    tags=["tour-routes"],
    responses={404: {"description": "Not found"}},
)


@router.get("/list", summary="获取游览路线列表")
async def get_route_list(
    currentPage: int = 1,
    pageSize: int = 10,
    theme: str | None = None,
    user_id: int = Depends(get_current_user_info),
):
    routes, total = await get_db_tour_routes(user_id, currentPage, pageSize, theme)

    # 为每条路线填充景点名称
    routes_data = []
    for route in routes:
        spots = await get_route_spots(route.route_id)
        spot_names = [s.spot_name for s in spots]
        routes_data.append({
            "route_id": route.route_id,
            "name": route.name,
            "theme": route.theme,
            "estimated_time_minutes": route.estimated_time_minutes,
            "description": route.description,
            "spot_count": len(spots),
            "spot_names": spot_names,
        })

    return make_return_data(
        True,
        ResultCode.SUCCESS,
        "成功",
        {"route_list": routes_data, "currentPage": currentPage, "pageSize": pageSize, "totalSize": total},
    )


@router.get("/info/{routeId}", summary="获取路线详情")
async def get_route_detail(routeId: int, user_id: int = Depends(get_current_user_info)):
    route = await get_db_tour_route_detail(routeId, user_id)
    if not route:
        return make_return_data(False, ResultCode.FAIL, "路线不存在", "")

    spots = await get_route_spots(routeId)
    spot_list = [
        {
            "spot_id": s.spot_id,
            "spot_name": s.spot_name,
            "category": s.category,
            "description": s.description,
            "image_path": s.image_path,
        }
        for s in spots
    ]

    return make_return_data(
        True,
        ResultCode.SUCCESS,
        "成功",
        {
            "route_id": route.route_id,
            "name": route.name,
            "theme": route.theme,
            "estimated_time_minutes": route.estimated_time_minutes,
            "description": route.description,
            "spots": spot_list,
        },
    )


@router.post("/create", summary="创建游览路线")
async def create_new_route(new_route: TourRouteCreate, user_id: int = Depends(get_current_user_info)):
    try:
        route = await create_tour_route(new_route, user_id)
        return make_return_data(True, ResultCode.SUCCESS, "创建成功", {"route_id": route.route_id})
    except Exception as e:
        logger.error(f"Create route failed: {e}")
        return make_return_data(False, ResultCode.FAIL, f"创建失败: {e}", "")


@router.put("/edit/{route_id}", summary="编辑游览路线")
async def edit_route(route_id: int, new_route: TourRouteCreate, user_id: int = Depends(get_current_user_info)):
    try:
        success = await update_tour_route(route_id, new_route, user_id)
    except ValueError as exc:
        return make_return_data(False,ResultCode.FAIL,str(exc),'')
    if not success:
        return make_return_data(False, ResultCode.FAIL, "编辑失败", "")
    return make_return_data(True, ResultCode.SUCCESS, "编辑成功", "")


@router.delete("/delete/{routeId}", summary="删除游览路线")
async def remove_route(routeId: int, user_id: int = Depends(get_current_user_info)):
    success = await delete_tour_route(routeId, user_id)
    if not success:
        return make_return_data(False, ResultCode.FAIL, "删除失败", "")
    return make_return_data(True, ResultCode.SUCCESS, "成功", "")


@router.post("/recommend", summary="个性化路线推荐")
async def get_route_recommendation(
    request: RouteRecommendRequest,
):
    """根据游客偏好推荐游览路线（免登录）"""
    # 获取所有可用景点
    spot_list, _ = await get_db_scenic_spot_info(user_id=1)

    if not spot_list:
        return make_return_data(False, ResultCode.FAIL, "暂无可用景点", "")

    # 调用推荐算法
    result = await recommend_route(request.preferences, spot_list, request.time_budget_minutes,
                                   city=request.city, pace=request.pace, start_area=request.start_area,
                                   end_area=request.end_area, queue_reserve_minutes=request.queue_reserve_minutes,
                                   excluded_spot_ids=request.excluded_spot_ids)
    if not result['spot_ids']:
        return make_return_data(False,ResultCode.FAIL,'当前时间与步行节奏下暂无匹配路线，请增加时长或调整出发区域','')

    return make_return_data(True, ResultCode.SUCCESS, "推荐成功", result)


@router.post("/parse-preferences", summary="从消息中解析游客偏好")
async def parse_visitor_preferences(request: PreferenceItem):
    """从游客消息中解析兴趣偏好"""
    if not request.preferences:
        return make_return_data(True, ResultCode.SUCCESS, "成功", {"preferences": ["comprehensive"]})

    # 如果已经提供了明确的偏好标签，直接返回
    valid_prefs = [p for p in request.preferences if p in ["history", "nature", "photography", "family", "comprehensive"]]
    if valid_prefs:
        return make_return_data(True, ResultCode.SUCCESS, "成功", {"preferences": valid_prefs})

    return make_return_data(True, ResultCode.SUCCESS, "成功", {"preferences": ["comprehensive"]})
