#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    :   knowledge_doc_db.py
@Time    :   2026/06/10
@Project :   景区导览AI数字人
@Desc    :   知识库文档数据表读写
"""

from typing import List, Tuple

from loguru import logger
from sqlalchemy import func
from sqlmodel import Session, and_, select

from ..models.tour_models import KnowledgeDocument
from .init_db import DB_ENGINE


async def get_db_knowledge_docs(
    user_id: int,
    current_page: int = -1,
    page_size: int = 10,
) -> Tuple[List[KnowledgeDocument], int]:
    """查询知识库文档列表

    Args:
        user_id: 用户 ID
        current_page: 页数，-1 表示全部
        page_size: 每页大小

    Returns:
        List[KnowledgeDocument]: 文档列表
        int: 总数
    """
    query_condition = and_(KnowledgeDocument.user_id == user_id)

    with Session(DB_ENGINE) as session:
        total_count = session.scalar(select(func.count(KnowledgeDocument.doc_id)).where(query_condition))

        if current_page < 0:
            docs = session.exec(
                select(KnowledgeDocument).where(query_condition).order_by(KnowledgeDocument.upload_time.desc())
            ).all()
        else:
            offset_idx = (current_page - 1) * page_size
            docs = session.exec(
                select(KnowledgeDocument)
                .where(query_condition)
                .offset(offset_idx)
                .limit(page_size)
                .order_by(KnowledgeDocument.upload_time.desc())
            ).all()

    if docs is None:
        docs = []

    return docs, total_count


async def add_knowledge_doc(doc: KnowledgeDocument) -> KnowledgeDocument:
    """添加知识库文档记录

    Args:
        doc: 文档信息

    Returns:
        KnowledgeDocument: 创建的文档
    """
    with Session(DB_ENGINE) as session:
        session.add(doc)
        session.commit()
        session.refresh(doc)
    return doc


async def update_doc_status(doc_id: int, status: str, chunk_count: int = 0) -> bool:
    """更新文档处理状态

    Args:
        doc_id: 文档 ID
        status: 新状态
        chunk_count: 分块数

    Returns:
        bool: 是否成功
    """
    try:
        with Session(DB_ENGINE) as session:
            doc = session.exec(
                select(KnowledgeDocument).where(KnowledgeDocument.doc_id == doc_id)
            ).one()
            if doc:
                doc.status = status
                doc.chunk_count = chunk_count
                session.add(doc)
                session.commit()
        return True
    except Exception as e:
        logger.error(f"Update doc status failed: {e}")
        return False


async def delete_knowledge_doc(doc_id: int, user_id: int) -> bool:
    """删除知识库文档

    Args:
        doc_id: 文档 ID
        user_id: 用户 ID

    Returns:
        bool: 是否成功
    """
    try:
        with Session(DB_ENGINE) as session:
            doc = session.exec(
                select(KnowledgeDocument).where(
                    and_(KnowledgeDocument.doc_id == doc_id, KnowledgeDocument.user_id == user_id)
                )
            ).one()
            if doc:
                session.delete(doc)
                session.commit()
                return True
        return False
    except Exception as e:
        logger.error(f"Delete doc failed: {e}")
        return False


async def get_all_knowledge_file_paths(user_id: int) -> List[str]:
    """获取所有知识库文档的文件路径（用于RAG重建）

    Args:
        user_id: 用户 ID

    Returns:
        List[str]: 文件路径列表
    """
    with Session(DB_ENGINE) as session:
        docs = session.exec(
            select(KnowledgeDocument).where(
                and_(KnowledgeDocument.user_id == user_id, KnowledgeDocument.status == "completed")
            )
        ).all()

    if docs is None:
        return []

    return [doc.file_path for doc in docs]
