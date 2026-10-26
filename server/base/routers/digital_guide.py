#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    :   digital_guide.py
@Time    :   2026/06/10
@Project :   景区导览AI数字人
@Desc    :   数字导游管理接口
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from pydantic import BaseModel
from ..database.init_db import DB_ENGINE
from ..modules.xingyun_access import require_guide_admin, selectable

from ..database.digital_guide_db import (
    create_or_update_db_guide_by_id,
    delete_digital_guide_by_id,
    get_db_digital_guides,
)
from ..models.tour_models import DigitalGuideInfo
from ..modules.guide_identity import SHOWCASE_GUIDE_NAME
from ..utils import ResultCode, make_return_data
from .users import get_current_user_info

router = APIRouter(
    prefix="/digital-guide",
    tags=["digital-guide"],
    responses={404: {"description": "Not found"}},
)


@router.get("/list", summary="获取数字导游列表")
async def get_guide_list(
    currentPage: int = 1,
    pageSize: int = 10,
    name: str | None = None,
    user_id: int = Depends(require_guide_admin),
):
    guides, total = await get_db_digital_guides(user_id, currentPage, pageSize)

    return make_return_data(
        True, ResultCode.SUCCESS, "成功",
        {"guide_list": guides, "currentPage": currentPage, "pageSize": pageSize, "totalSize": total},
    )


@router.get("/info/{guideId}", summary="获取数字导游详情")
async def get_guide_detail(guideId: int, user_id: int = Depends(require_guide_admin)):
    guides, _ = await get_db_digital_guides(user_id, guide_id=guideId)
    if not guides:
        return make_return_data(False, ResultCode.FAIL, "导游不存在", "")
    return make_return_data(True, ResultCode.SUCCESS, "成功", guides[0])


@router.post("/create", summary="新增数字导游")
async def create_guide(new_info: DigitalGuideInfo, user_id: int = Depends(require_guide_admin)):
    new_info.guide_id = None
    if not new_info.poster_image or not new_info.avatar:
        return make_return_data(False, ResultCode.FAIL, "请上传数字人全身形象和头像", "")
    success = create_or_update_db_guide_by_id(0, new_info, user_id)
    if not success:
        return make_return_data(False, ResultCode.FAIL, "创建失败", "")
    return make_return_data(True, ResultCode.SUCCESS, "创建成功", "")


@router.put("/edit/{guide_id}", summary="编辑数字导游")
async def edit_guide(guide_id: int, new_info: DigitalGuideInfo, user_id: int = Depends(require_guide_admin)):
    if not new_info.poster_image or not new_info.avatar:
        return make_return_data(False, ResultCode.FAIL, "请上传数字人全身形象和头像", "")
    success = create_or_update_db_guide_by_id(guide_id, new_info, user_id)
    if not success:
        return make_return_data(False, ResultCode.FAIL, "编辑失败", "")
    return make_return_data(True, ResultCode.SUCCESS, "编辑成功", "")


@router.delete("/delete/{guideId}", summary="删除数字导游")
async def delete_guide(guideId: int, user_id: int = Depends(require_guide_admin)):
    guides, _ = await get_db_digital_guides(user_id, guide_id=guideId)
    success = await delete_digital_guide_by_id(guideId, user_id)
    if not success:
        return make_return_data(False, ResultCode.FAIL, "删除失败", "")
    return make_return_data(True, ResultCode.SUCCESS, "删除成功", "")


class PublicationInput(BaseModel):
    is_enabled: bool


@router.put("/publication/{guide_id}", summary="上架或下架数字导游")
def publish_guide(guide_id: int, data: PublicationInput, user_id: int = Depends(require_guide_admin)):
    with Session(DB_ENGINE) as db:
        guide = db.get(DigitalGuideInfo, guide_id)
        if not guide or guide.delete or guide.user_id != user_id:
            raise HTTPException(404, "导游不存在或无权管理")
        guide.is_enabled = data.is_enabled
        if data.is_enabled and not selectable(db, guide):
            raise HTTPException(400, "请先完成星云应用绑定")
        db.add(guide)
        db.commit()
    return make_return_data(True, ResultCode.SUCCESS, "已上架" if data.is_enabled else "已下架", {"is_enabled": data.is_enabled})
