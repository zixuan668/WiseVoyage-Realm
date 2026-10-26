#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    :   scenic_spot_db.py
@Time    :   2026/06/10
@Project :   景区导览AI数字人
@Desc    :   景区景点数据表读写
"""

from typing import List, Tuple

from loguru import logger
from sqlalchemy import func
from sqlmodel import Session, and_, not_, select

from ...web_configs import API_CONFIG
from ..models.tour_models import ScenicSpotInfo
from .init_db import DB_ENGINE


async def get_db_scenic_spot_info(
    user_id: int,
    current_page: int = -1,
    page_size: int = 10,
    spot_name: str | None = None,
    spot_id: int | None = None,
    category: str | None = None,
    exclude_list: List[int] | None = None,
) -> Tuple[List[ScenicSpotInfo], int]:
    """查询数据库中的景点信息

    Args:
        user_id: 用户 ID
        current_page: 页数，-1 表示全部
        page_size: 每页大小
        spot_name: 景点名称模糊搜索
        spot_id: 特定景点 ID
        category: 按分类筛选
        exclude_list: 排除的 ID 列表

    Returns:
        List[ScenicSpotInfo]: 景点信息列表
        int: 总数
    """

    assert current_page != 0
    assert page_size != 0

    query_condition = and_(ScenicSpotInfo.user_id == user_id, ScenicSpotInfo.delete == False)

    if spot_name:
        query_condition = and_(query_condition, ScenicSpotInfo.spot_name.ilike(f"%{spot_name}%"))
    if spot_id is not None:
        query_condition = and_(query_condition, ScenicSpotInfo.spot_id == spot_id)
    if category:
        query_condition = and_(query_condition, ScenicSpotInfo.category == category)
    if exclude_list:
        query_condition = and_(query_condition, not_(ScenicSpotInfo.spot_id.in_(exclude_list)))

    with Session(DB_ENGINE) as session:
        total_spot_num = session.scalar(select(func.count(ScenicSpotInfo.spot_id)).where(query_condition))
        if current_page < 0:
            spot_list = session.exec(
                select(ScenicSpotInfo).where(query_condition).order_by(ScenicSpotInfo.spot_id)
            ).all()
        else:
            offset_idx = (current_page - 1) * page_size
            spot_list = session.exec(
                select(ScenicSpotInfo)
                .where(query_condition)
                .offset(offset_idx)
                .limit(page_size)
                .order_by(ScenicSpotInfo.spot_id)
            ).all()

    if spot_list is None:
        logger.warning("nothing to find in db...")
        spot_list = []

    for spot in spot_list:
        spot.image_path = (API_CONFIG.REQUEST_FILES_URL.rstrip('/') + '/' + spot.image_path.lstrip('/')) if spot.image_path else ''
        spot.instruction = (API_CONFIG.REQUEST_FILES_URL.rstrip('/') + '/' + spot.instruction.lstrip('/')) if spot.instruction else ''

    return spot_list, total_spot_num


async def delete_scenic_spot_by_id(spot_id: int, user_id: int) -> bool:
    """软删除特定景点

    Args:
        spot_id: 景点 ID
        user_id: 用户 ID

    Returns:
        bool: 是否删除成功
    """
    delete_success = True
    try:
        with Session(DB_ENGINE) as session:
            spot_info = session.exec(
                select(ScenicSpotInfo).where(
                    and_(ScenicSpotInfo.spot_id == spot_id, ScenicSpotInfo.user_id == user_id)
                )
            ).one()

            if spot_info is None:
                logger.error("Delete by other ID !!!")
                return False

            spot_info.delete = True
            session.add(spot_info)
            session.commit()
    except Exception:
        delete_success = False

    return delete_success


def create_or_update_db_spot_by_id(spot_id: int, new_info: ScenicSpotInfo, user_id: int) -> bool:
    """新增或编辑景点信息

    Args:
        spot_id: 景点 ID（0 表示新增）
        new_info: 新的景点信息
        user_id: 用户 ID

    Returns:
        bool: 知识文档是否变化
    """
    instruction_updated = False

    new_info.image_path = new_info.image_path.replace(API_CONFIG.REQUEST_FILES_URL, "")
    new_info.instruction = new_info.instruction.replace(API_CONFIG.REQUEST_FILES_URL, "")

    with Session(DB_ENGINE) as session:
        if spot_id > 0:
            spot_info = session.exec(
                select(ScenicSpotInfo).where(
                    and_(ScenicSpotInfo.spot_id == spot_id, ScenicSpotInfo.user_id == user_id)
                )
            ).one()

            if spot_info is None:
                logger.error("Edit by other ID !!!")
                return False

            if spot_info.instruction != new_info.instruction:
                instruction_updated = True

            spot_info.spot_name = new_info.spot_name
            spot_info.category = new_info.category
            spot_info.tags = new_info.tags
            spot_info.location = new_info.location
            spot_info.best_season = new_info.best_season
            spot_info.description = new_info.description
            spot_info.history_detail = new_info.history_detail
            spot_info.image_path = new_info.image_path
            spot_info.instruction = new_info.instruction

            session.add(spot_info)
        else:
            session.add(new_info)
            instruction_updated = True

        session.commit()
    return instruction_updated
