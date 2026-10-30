#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    :   analytics_db.py
@Time    :   2026/06/10
@Project :   景区导览AI数字人
@Desc    :   数据分析数据表读写
"""

from datetime import datetime
from typing import List

from loguru import logger
from sqlalchemy import func
from sqlmodel import Session, and_, select

from ..models.tour_models import (
    DailyInteractionStats,
    ScenicSpotInfo,
    TourRouteSpot,
    TourSessionInfo,
    TourSessionStatus,
    VisitorFeedback,
    VisitorInteraction,
)
from .init_db import DB_ENGINE


async def get_visitor_interactions(
    session_id: int | None = None,
    limit: int = 100,
) -> List[VisitorInteraction]:
    """获取游客交互记录

    Args:
        session_id: 会话 ID（None 表示全部）
        limit: 最大返回数

    Returns:
        List[VisitorInteraction]: 交互记录
    """
    with Session(DB_ENGINE) as session:
        if session_id:
            interactions = session.exec(
                select(VisitorInteraction)
                .where(VisitorInteraction.session_id == session_id)
                .order_by(VisitorInteraction.send_time)
            ).all()
        else:
            interactions = session.exec(
                select(VisitorInteraction)
                .order_by(VisitorInteraction.send_time.desc())
                .limit(limit)
            ).all()

    return interactions or []


async def save_visitor_feedback(feedback: VisitorFeedback) -> VisitorFeedback:
    """保存游客反馈

    Args:
        feedback: 反馈信息

    Returns:
        VisitorFeedback: 保存后的反馈
    """
    with Session(DB_ENGINE) as session:
        session.add(feedback)
        session.commit()
        session.refresh(feedback)
    return feedback


async def get_feedback_list(
    user_id: int,
    current_page: int = 1,
    page_size: int = 10,
) -> tuple:
    """获取反馈列表"""
    query_condition = and_(VisitorFeedback.user_id == user_id)

    with Session(DB_ENGINE) as session:
        total_count = session.scalar(select(func.count(VisitorFeedback.feedback_id)).where(query_condition))

        offset_idx = (current_page - 1) * page_size
        feedbacks = session.exec(
            select(VisitorFeedback)
            .where(query_condition)
            .order_by(VisitorFeedback.created_at.desc())
            .offset(offset_idx)
            .limit(page_size)
        ).all()

    return feedbacks or [], total_count


async def get_daily_stats(date: datetime | None = None, user_id: int | None = None) -> DailyInteractionStats | None:
    """获取指定日期的运营统计

    Args:
        date: 日期
        user_id: 用户 ID

    Returns:
        DailyInteractionStats | None
    """
    with Session(DB_ENGINE) as session:
        if date:
            stats = session.exec(
                select(DailyInteractionStats).where(
                    and_(
                        DailyInteractionStats.user_id == user_id,
                        func.date(DailyInteractionStats.date) == date.date(),
                    )
                )
            ).first()
        else:
            stats = session.exec(
                select(DailyInteractionStats)
                .where(DailyInteractionStats.user_id == user_id)
                .order_by(DailyInteractionStats.date.desc())
            ).first()
    return stats


async def get_weekly_stats(user_id: int) -> List[DailyInteractionStats]:
    """获取最近7天的运营统计

    Args:
        user_id: 用户 ID

    Returns:
        List[DailyInteractionStats]: 统计列表
    """
    from datetime import timedelta

    seven_days_ago = datetime.now() - timedelta(days=7)

    with Session(DB_ENGINE) as session:
        stats = session.exec(
            select(DailyInteractionStats)
            .where(
                and_(
                    DailyInteractionStats.user_id == user_id,
                    DailyInteractionStats.date >= seven_days_ago,
                )
            )
            .order_by(DailyInteractionStats.date)
        ).all()

    return stats or []


async def get_sentiment_summary(user_id: int) -> dict:
    """获取情感分析汇总

    Args:
        user_id: 用户 ID

    Returns:
        dict: 情感汇总数据
    """
    with Session(DB_ENGINE) as session:
        interactions = session.exec(
            select(VisitorInteraction).order_by(VisitorInteraction.send_time.desc()).limit(500)
        ).all()

    if not interactions:
        return {"positive": 0, "neutral": 0, "negative": 0, "total": 0}

    positive = sum(1 for i in interactions if i.emotion_label == "positive")
    neutral = sum(1 for i in interactions if i.emotion_label == "neutral")
    negative = sum(1 for i in interactions if i.emotion_label == "negative")

    return {
        "positive": positive,
        "neutral": neutral,
        "negative": negative,
        "total": len(interactions),
        "positive_rate": round(positive / len(interactions) * 100, 1) if interactions else 0,
    }


async def get_service_stats(user_id: int) -> dict:
    """获取服务统计数据（当前服务日/服务周）。

    服务日默认按本地时间 06:00 换日：凌晨仍在上演的晚间导览算作“今日”，
    避免 0 点后看板被清零。可用 ANALYTICS_DAY_START_HOUR 调整。
    """
    from ..modules.analytics_time import service_day_window, service_week_window

    day_start, day_end = service_day_window()
    week_start, _ = service_week_window()

    with Session(DB_ENGINE) as session:
        base_session_filter = (
            TourSessionInfo.user_id == user_id,
            TourSessionInfo.delete == False,
        )
        session_join = select(func.count(TourSessionInfo.session_id)).join(
            TourSessionStatus, TourSessionInfo.status_id == TourSessionStatus.status_id
        )

        # 今日会话数（按会话开始时间落在当前服务日内）
        today_sessions = session.scalar(
            session_join.where(
                and_(
                    *base_session_filter,
                    TourSessionStatus.start_time >= day_start,
                    TourSessionStatus.start_time < day_end,
                )
            )
        ) or 0

        # 今日提问数
        today_questions = session.scalar(
            select(func.count(VisitorInteraction.message_id)).where(
                and_(
                    VisitorInteraction.role == "user",
                    VisitorInteraction.send_time >= day_start,
                    VisitorInteraction.send_time < day_end,
                )
            )
        ) or 0

        # 本周会话数（按会话开始时间落在当前服务周内）
        week_sessions = session.scalar(
            session_join.where(
                and_(
                    *base_session_filter,
                    TourSessionStatus.start_time >= week_start,
                    TourSessionStatus.start_time < day_end,
                )
            )
        ) or 0

    return {
        "today_sessions": today_sessions,
        "today_questions": today_questions,
        "week_sessions": week_sessions,
    }


# =======================================================
#   新增：综合数据分析查询函数
# =======================================================


async def get_hot_spot_ranking(limit: int = 10) -> list:
    """热门景点排行（按会话中出现的次数）"""
    from ..models.tour_models import ScenicSpotInfo, TourSessionInfo as TSI

    with Session(DB_ENGINE) as session:
        # 统计每个景点的会话数（通过路线关联）
        spots = session.exec(
            select(ScenicSpotInfo).where(ScenicSpotInfo.delete == False)
        ).all()

        import json
        from collections import Counter, defaultdict
        route_spots = defaultdict(set)
        for link in session.exec(select(TourRouteSpot)).all():
            route_spots[link.route_id].add(link.spot_id)
        counts = Counter()
        tours = session.exec(select(TSI).where(TSI.delete == False)).all()
        for tour in tours:
            try:
                preferences = json.loads(tour.visitor_preferences or '{}')
            except (ValueError, TypeError):
                preferences = {}
            if isinstance(preferences, dict) and 'spot_ids' in preferences:
                ids = preferences['spot_ids']
                ids = {sid for sid in ids if type(sid) is int} if isinstance(ids, list) else set()
            else:
                ids = route_spots.get(tour.route_id, set())
            counts.update(ids)
        ranking = [{
            'spot_id': spot.spot_id, 'spot_name': spot.spot_name,
            'category': spot.category, 'session_count': counts[spot.spot_id],
        } for spot in spots]
        # 按会话数降序排列
        ranking.sort(key=lambda x: x["session_count"], reverse=True)
        return ranking[:limit]


async def get_daily_service_trend(days: int = 30) -> list:
    """获取N天服务趋势数据"""
    from datetime import timedelta

    today = datetime.now().date()
    trend = []

    with Session(DB_ENGINE) as session:
        for i in range(days - 1, -1, -1):
            day = today - timedelta(days=i)
            day_start = datetime(day.year, day.month, day.day)
            day_end = day_start + timedelta(days=1)

            # 当天会话数
            day_sessions = session.scalar(
                select(func.count(TourSessionStatus.status_id)).where(
                    and_(
                        TourSessionStatus.start_time >= day_start,
                        TourSessionStatus.start_time < day_end,
                    )
                )
            ) or 0

            # 当天提问数
            day_questions = session.scalar(
                select(func.count(VisitorInteraction.message_id)).where(
                    and_(
                        VisitorInteraction.role == "user",
                        VisitorInteraction.send_time >= day_start,
                        VisitorInteraction.send_time < day_end,
                    )
                )
            ) or 0

            # 当天满意度
            day_interactions = session.exec(
                select(VisitorInteraction).where(
                    and_(
                        VisitorInteraction.send_time >= day_start,
                        VisitorInteraction.send_time < day_end,
                        VisitorInteraction.sentiment_score > 0,
                    )
                )
            ).all()
            if day_interactions:
                scores = [it.sentiment_score for it in day_interactions if it.sentiment_score > 0]
                day_satisfaction = round(sum(scores) / len(scores) * 100, 1) if scores else 0
            else:
                day_satisfaction = 0

            trend.append({
                "date": day.strftime("%m-%d"),
                "sessions": day_sessions,
                "questions": day_questions,
                "satisfaction": day_satisfaction,
            })

    return trend


async def get_hourly_distribution(days: int = 7) -> list:
    """获取时段分布数据（24小时×N天的活跃度热力图数据）"""
    from datetime import timedelta

    today = datetime.now().date()
    start_date = today - timedelta(days=days - 1)

    with Session(DB_ENGINE) as session:
        interactions = session.exec(
            select(VisitorInteraction).where(
                and_(
                    VisitorInteraction.send_time >= datetime(start_date.year, start_date.month, start_date.day),
                    VisitorInteraction.role == "user",
                )
            )
        ).all()

    # 构建24×7的矩阵
    hourly_data = {}
    for it in (interactions or []):
        if it.send_time:
            hour = it.send_time.hour
            day_of_week = it.send_time.weekday()  # 0=Mon, 6=Sun
            key = f"{day_of_week}_{hour}"
            hourly_data[key] = hourly_data.get(key, 0) + 1

    # 转为前端热力图需要的格式
    weekdays_cn = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    result = []
    for day_idx in range(7):
        for hour in range(24):
            key = f"{day_idx}_{hour}"
            count = hourly_data.get(key, 0)
            result.append({
                "day": weekdays_cn[day_idx],
                "hour": f"{hour:02d}:00",
                "count": count,
            })

    return result


async def get_global_emotion_stats() -> dict:
    """获取全局情感统计数据"""
    with Session(DB_ENGINE) as session:
        total = session.scalar(
            select(func.count(VisitorInteraction.message_id)).where(VisitorInteraction.role == "user")
        ) or 0

        positive = session.scalar(
            select(func.count(VisitorInteraction.message_id)).where(
                and_(VisitorInteraction.role == "user", VisitorInteraction.emotion_label == "positive")
            )
        ) or 0

        neutral = session.scalar(
            select(func.count(VisitorInteraction.message_id)).where(
                and_(VisitorInteraction.role == "user", VisitorInteraction.emotion_label == "neutral")
            )
        ) or 0

        negative = session.scalar(
            select(func.count(VisitorInteraction.message_id)).where(
                and_(VisitorInteraction.role == "user", VisitorInteraction.emotion_label == "negative")
            )
        ) or 0

    return {
        "total": total,
        "positive": positive,
        "neutral": neutral,
        "negative": negative,
        "positive_rate": round(positive / total * 100, 1) if total > 0 else 0,
        "negative_rate": round(negative / total * 100, 1) if total > 0 else 0,
    }


async def save_analytics_report(report_type: str, content: str, user_id: int = 1) -> int:
    """保存分析报告到 visitor_feedback 表（复用现有表结构）

    Args:
        report_type: daily / weekly / session
        content: 报告内容（JSON字符串）
        user_id: 用户ID

    Returns:
        int: 反馈ID
    """
    report_labels = {
        "daily": "日报告",
        "weekly": "周报告",
        "session": "会话报告",
    }
    feedback = VisitorFeedback(
        session_id=None,  # 分析报告不关联具体会话
        overall_emotion_label=report_labels.get(report_type, "报告"),
        overall_sentiment_score=0.0,
        feedback_text=content,
        topics="[]",
        user_id=user_id,
    )
    with Session(DB_ENGINE) as session:
        session.add(feedback)
        session.commit()
        session.refresh(feedback)
    return feedback.feedback_id


async def get_analytics_reports(report_type: str | None = None, limit: int = 20) -> list:
    """获取历史分析报告列表"""
    report_labels = {
        "daily": "日报告",
        "weekly": "周报告",
    }
    label_filter = report_labels.get(report_type, "") if report_type else ""

    with Session(DB_ENGINE) as session:
        if label_filter:
            feedbacks = session.exec(
                select(VisitorFeedback)
                .where(VisitorFeedback.overall_emotion_label == label_filter)
                .order_by(VisitorFeedback.created_at.desc())
                .limit(limit)
            ).all()
        else:
            # 获取所有报告（emotion_label 为报告类型标签的记录）
            all_labels = list(report_labels.values())
            feedbacks = session.exec(
                select(VisitorFeedback)
                .where(VisitorFeedback.overall_emotion_label.in_(all_labels))
                .order_by(VisitorFeedback.created_at.desc())
                .limit(limit)
            ).all()

    return [
        {
            "report_id": fb.feedback_id,
            "report_type": fb.overall_emotion_label,
            "content": fb.feedback_text,
            "created_at": str(fb.created_at) if fb.created_at else "",
        }
        for fb in (feedbacks or [])
    ]
