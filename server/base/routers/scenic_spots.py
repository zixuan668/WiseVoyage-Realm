#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    :   scenic_spots.py
@Time    :   2026/06/10
@Project :   景区导览AI数字人
@Desc    :   景区景点管理接口
"""

import re
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger

from ...web_configs import API_CONFIG, WEB_CONFIGS
from ..database.scenic_spot_db import (
    create_or_update_db_spot_by_id,
    delete_scenic_spot_by_id,
    get_db_scenic_spot_info,
)
from ..models.tour_models import ScenicSpotInfo, SpotPageItem
from ..modules.rag.rag_worker import rebuild_tour_rag_db
from ..utils import ResultCode, make_return_data
from .users import get_current_user_info

router = APIRouter(
    prefix="/scenic-spots",
    tags=["scenic-spots"],
    responses={404: {"description": "Not found"}},
)


@router.get("/list", summary="获取分页景点信息")
async def get_scenic_spot_list(
    currentPage: int = 1,
    pageSize: int = 10,
    spotName: str | None = None,
    category: str | None = None,
    user_id: int = Depends(get_current_user_info),
):
    """获取景点列表（支持按名称/分类搜索）"""
    spot_list, total_size = await get_db_scenic_spot_info(
        user_id=user_id,
        current_page=currentPage,
        page_size=pageSize,
        spot_name=spotName,
        category=category,
    )

    res_data = SpotPageItem(
        spot_list=spot_list,
        currentPage=currentPage,
        pageSize=pageSize,
        totalSize=total_size,
    )
    return make_return_data(True, ResultCode.SUCCESS, "成功", res_data)


@router.get("/info/{spotId}", summary="获取特定景点详细信息")
async def get_scenic_spot_detail(spotId: int, user_id: int = Depends(get_current_user_info)):
    spot_list, _ = await get_db_scenic_spot_info(user_id=user_id, spot_id=spotId)

    if len(spot_list) == 1:
        spot_list = spot_list[0]

    return make_return_data(True, ResultCode.SUCCESS, "成功", spot_list)


@router.get('/instruction/{spot_id}', summary='获取景点游览说明')
async def get_spot_instruction(spot_id: int, user_id: int = Depends(get_current_user_info)):
    spots, _ = await get_db_scenic_spot_info(user_id=user_id, spot_id=spot_id)
    if not spots or not spots[0].instruction:
        raise HTTPException(404, '景点游览说明不存在')
    from urllib.parse import unquote
    relative = unquote(spots[0].instruction.removeprefix(API_CONFIG.REQUEST_FILES_URL)).lstrip('/')
    root = Path(WEB_CONFIGS.SERVER_FILE_ROOT).resolve()
    document = (root / relative).resolve()
    if not document.is_relative_to(root) or not document.is_file():
        raise HTTPException(404, '景点游览说明不存在')
    return make_return_data(True, ResultCode.SUCCESS, '成功', document.read_text(encoding='utf-8-sig'))


@router.post("/create", summary="新增景点")
async def create_scenic_spot(upload_item: ScenicSpotInfo, user_id: int = Depends(get_current_user_info)):
    upload_item.user_id = user_id
    upload_item.spot_id = None

    rebuild_flag = create_or_update_db_spot_by_id(0, upload_item, user_id)

    if WEB_CONFIGS.ENABLE_RAG and rebuild_flag:
        await rebuild_tour_rag_db(user_id)

    return make_return_data(True, ResultCode.SUCCESS, "成功", "")


@router.put("/edit/{spot_id}", summary="编辑景点")
async def edit_scenic_spot(spot_id: int, upload_item: ScenicSpotInfo, user_id: int = Depends(get_current_user_info)):
    rebuild_flag = create_or_update_db_spot_by_id(spot_id, upload_item, user_id)

    if WEB_CONFIGS.ENABLE_RAG and rebuild_flag:
        await rebuild_tour_rag_db(user_id)

    return make_return_data(True, ResultCode.SUCCESS, "成功", "")


@router.delete("/delete/{spotId}", summary="删除景点")
async def delete_scenic_spot(spotId: int, user_id: int = Depends(get_current_user_info)):
    success = await delete_scenic_spot_by_id(spotId, user_id)

    if not success:
        return make_return_data(False, ResultCode.FAIL, "删除失败", "")

    if WEB_CONFIGS.ENABLE_RAG:
        await rebuild_tour_rag_db(user_id)

    return make_return_data(True, ResultCode.SUCCESS, "成功", "")


@router.post("/ai-generate", summary="AI生成景点描述和历史详情（基于游览说明.md）")
async def ai_generate_spot_content(
    spot_name: str = "",
    user_id: int = Depends(get_current_user_info),
):
    """读取 游览说明/ 文件夹中的 .md 文档，调用 LLM 生成 description 和 history_detail"""
    import json
    from ..routers.llm import get_llm_res

    if not spot_name.strip():
        return make_return_data(False, ResultCode.FAIL, "请输入景点名称", "")

    # 扫描游览说明文件夹
    guide_dir = Path("游览说明")
    if not guide_dir.exists():
        return make_return_data(False, ResultCode.FAIL, "游览说明文件夹不存在，请先创建并放入 .md 文档", "")

    md_files = list(guide_dir.glob("*.md"))
    if not md_files:
        return make_return_data(False, ResultCode.FAIL, "游览说明文件夹中没有 .md 文件", "")

    # 读取所有 .md 文件内容，找最匹配的
    guide_content = ""
    for md_file in md_files:
        try:
            with open(md_file, "r", encoding="utf-8") as f:
                content = f.read()
            # 如果文件内容包含景点名称，优先使用
            if spot_name in content or spot_name in md_file.stem:
                guide_content = content
                break
        except Exception:
            continue

    # 如果没找到匹配的，用第一个文件
    if not guide_content:
        try:
            with open(md_files[0], "r", encoding="utf-8") as f:
                guide_content = f.read()
        except Exception:
            return make_return_data(False, ResultCode.FAIL, "无法读取游览说明文件", "")

    # 截取合适长度（避免超过 LLM 上下文）
    if len(guide_content) > 3000:
        guide_content = guide_content[:3000]

    prompt = [
        {
            "role": "system",
            "content": (
                "你是一个景区内容编辑专家。请根据提供的游览说明文档，为指定景点生成两个字段的内容。"
                "必须严格基于文档中的事实信息，不要编造。"
                "只返回 JSON 格式：{\"description\": \"...\", \"history_detail\": \"...\"}"
            ),
        },
        {
            "role": "user",
            "content": (
                f"## 景点名称\n{spot_name.strip()}\n\n"
                f"## 游览说明文档\n{guide_content}\n\n"
                f"请根据文档内容，为该景点生成：\n"
                f"1. description（景点简介，150-300字，概括景点的核心特色和主要看点）\n"
                f"2. history_detail（历史详情，200-500字，介绍景点的历史沿革、文化背景和相关典故）\n\n"
                f"只返回 JSON，格式：{{\"description\": \"...\", \"history_detail\": \"...\"}}"
            ),
        },
    ]

    try:
        logger.info(f"[AI-Generate] Generating for spot: {spot_name}")
        response = await get_llm_res(prompt)
        logger.info(f"[AI-Generate] Response length: {len(response)}")
    except Exception as e:
        logger.error(f"[AI-Generate] LLM call failed: {e}")
        return make_return_data(False, ResultCode.FAIL, f"AI服务调用失败: {str(e)}", "")

    # 解析 JSON
    result = {"description": "", "history_detail": ""}
    try:
        # 尝试匹配完整 JSON 块
        json_match = re.search(
            r'\{\s*"description"\s*:\s*".*?"\s*,\s*"history_detail"\s*:\s*".*?"\s*\}',
            response, re.DOTALL
        )
        if json_match:
            result = json.loads(json_match.group())
    except Exception:
        pass

    # Fallback: 分别提取字段
    if not result.get("description"):
        desc_match = re.search(r'"description"\s*:\s*"([^"]*)"', response)
        if desc_match:
            result["description"] = desc_match.group(1)
    if not result.get("history_detail"):
        hist_match = re.search(r'"history_detail"\s*:\s*"([^"]*)"', response)
        if hist_match:
            result["history_detail"] = hist_match.group(1)

    return make_return_data(True, ResultCode.SUCCESS, "AI生成完成", {
        "description": result.get("description", ""),
        "history_detail": result.get("history_detail", ""),
    })
