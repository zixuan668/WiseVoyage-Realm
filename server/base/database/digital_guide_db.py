#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    :   digital_guide_db.py
@Time    :   2026/06/10
@Project :   景区导览AI数字人
@Desc    :   数字导游数据表读写
"""

from typing import List, Tuple

from loguru import logger
from sqlalchemy import func
from sqlmodel import Session, and_, select

from ...web_configs import API_CONFIG
from ..models.tour_models import DigitalGuideInfo
from .init_db import DB_ENGINE


def _asset_url(path: str) -> str:
    """将数据库中的相对资源路径转换为可访问 URL，兼容有无前导斜杠。"""
    if not path or path.startswith(("http://", "https://")):
        return path
    return f"{API_CONFIG.REQUEST_FILES_URL.rstrip('/')}/{path.lstrip('/')}"


async def get_db_digital_guides(
    user_id: int,
    current_page: int = -1,
    page_size: int = 10,
    guide_id: int | None = None,
) -> Tuple[List[DigitalGuideInfo], int]:
    """查询数字导游列表

    Args:
        user_id: 用户 ID
        current_page: 页数
        page_size: 每页大小
        guide_id: 特定导游 ID

    Returns:
        List[DigitalGuideInfo]: 导游列表
        int: 总数
    """
    query_condition = and_(DigitalGuideInfo.user_id == user_id, DigitalGuideInfo.delete == False)

    if guide_id is not None:
        query_condition = and_(query_condition, DigitalGuideInfo.guide_id == guide_id)

    with Session(DB_ENGINE) as session:
        total_count = session.scalar(select(func.count(DigitalGuideInfo.guide_id)).where(query_condition))

        if current_page < 0:
            guides = session.exec(
                select(DigitalGuideInfo).where(query_condition).order_by(DigitalGuideInfo.guide_id)
            ).all()
        else:
            offset_idx = (current_page - 1) * page_size
            guides = session.exec(
                select(DigitalGuideInfo)
                .where(query_condition)
                .offset(offset_idx)
                .limit(page_size)
                .order_by(DigitalGuideInfo.guide_id)
            ).all()

    if guides is None:
        guides = []

    # 转换路径
    for guide in guides:
        if guide.avatar:
            guide.avatar = _asset_url(guide.avatar)
        if guide.poster_image:
            guide.poster_image = _asset_url(guide.poster_image)
        if guide.base_mp4_path:
            guide.base_mp4_path = _asset_url(guide.base_mp4_path)
        if guide.tts_reference_audio:
            guide.tts_reference_audio = _asset_url(guide.tts_reference_audio)

    return guides, total_count


def create_or_update_db_guide_by_id(guide_id: int, new_info: DigitalGuideInfo, user_id: int) -> bool:
    """新增或编辑数字导游信息

    Args:
        guide_id: 导游 ID（0 表示新增）
        new_info: 新导游信息
        user_id: 用户 ID

    Returns:
        bool: 是否成功
    """
    success = True

    # 去掉服务器地址
    if new_info.avatar:
        new_info.avatar = new_info.avatar.replace(API_CONFIG.REQUEST_FILES_URL, "")
    if new_info.poster_image:
        new_info.poster_image = new_info.poster_image.replace(API_CONFIG.REQUEST_FILES_URL, "")
    if new_info.base_mp4_path:
        new_info.base_mp4_path = new_info.base_mp4_path.replace(API_CONFIG.REQUEST_FILES_URL, "")
    if new_info.tts_reference_audio:
        new_info.tts_reference_audio = new_info.tts_reference_audio.replace(API_CONFIG.REQUEST_FILES_URL, "")

    with Session(DB_ENGINE) as session:
        if guide_id > 0:
            guide_info = session.exec(
                select(DigitalGuideInfo).where(
                    and_(DigitalGuideInfo.guide_id == guide_id, DigitalGuideInfo.user_id == user_id)
                )
            ).first()

            if guide_info is None:
                logger.error("Edit by other ID !!!")
                return False

            guide_info.name = new_info.name
            guide_info.character = new_info.character
            guide_info.is_enabled = new_info.is_enabled
            guide_info.avatar = new_info.avatar
            guide_info.voice_style = new_info.voice_style
            guide_info.language = getattr(new_info, "language", "zh")
            guide_info.voice_speed = new_info.voice_speed
            guide_info.outfit_images = new_info.outfit_images
            guide_info.tts_weight_tag = new_info.tts_weight_tag
            guide_info.tts_reference_sentence = new_info.tts_reference_sentence
            guide_info.tts_reference_audio = new_info.tts_reference_audio
            guide_info.poster_image = new_info.poster_image
            if guide_info.base_mp4_path != new_info.base_mp4_path:
                guide_info.base_video_metadata = ""
            guide_info.base_mp4_path = new_info.base_mp4_path

            session.add(guide_info)
        else:
            new_info.user_id = user_id
            session.add(new_info)

        session.commit()
    return success


async def delete_digital_guide_by_id(guide_id: int, user_id: int) -> bool:
    """软删除数字导游

    Args:
        guide_id: 导游 ID
        user_id: 用户 ID

    Returns:
        bool: 是否删除成功
    """
    try:
        with Session(DB_ENGINE) as session:
            guide_info = session.exec(
                select(DigitalGuideInfo).where(
                    and_(DigitalGuideInfo.guide_id == guide_id, DigitalGuideInfo.user_id == user_id)
                )
            ).one()

            if guide_info is None:
                return False

            guide_info.delete = True
            session.add(guide_info)
            session.commit()
        return True
    except Exception:
        return False
