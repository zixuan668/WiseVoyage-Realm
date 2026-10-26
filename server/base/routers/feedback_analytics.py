#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    :   feedback_analytics.py
@Time    :   2026/06/10
@Project :   景区导览AI数字人
@Desc    :   游客反馈分析 & 运营数据看板接口
"""

import json
from collections import Counter
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from loguru import logger

from ..database.analytics_db import (
    get_global_emotion_stats,
    get_sentiment_summary,
    get_service_stats,
    get_visitor_interactions,
)
from ..database.tour_session_db import get_db_tour_sessions
from ..models.tour_models import VisitorFeedback
from ..modules.sentiment_analyzer import get_emotion_trend_analysis
from ..utils import ResultCode, make_return_data
from .users import get_current_user_info

router = APIRouter(
    prefix="/analytics",
    tags=["analytics"],
    responses={404: {"description": "Not found"}},
)


@router.get("/sentiment-report", summary="游客情感分析报告")
async def get_sentiment_report(
    session_id: int | None = None,
    user_id: int = Depends(get_current_user_info),
):
    """获取游客情感分析汇总报告（含总互动数、热门话题、热门提问）"""
    # 获取交互记录
    interactions = await get_visitor_interactions(session_id=session_id, limit=500)

    if not interactions:
        return make_return_data(
            True, ResultCode.SUCCESS, "暂无数据",
            {
                "overall_sentiment": "neutral",
                "total_interactions": 0, "positive_count": 0, "neutral_count": 0, "negative_count": 0,
                "positive_ratio": 0, "neutral_ratio": 0, "negative_ratio": 0,
                "top_positive_keywords": [], "top_negative_keywords": [],
                "hot_questions": [], "hot_topics": [],
                "comment_highlights": [], "suggestions": [],
            },
        )

    # 统计情感分布（分离用户消息和导游回复，只统计用户消息的情感）
    user_interactions = [i for i in interactions if i.role == "user"]
    guide_interactions = [i for i in interactions if i.role == "guide"]
    total = len(user_interactions)
    positive_count = sum(1 for i in user_interactions if i.emotion_label == "positive")
    neutral_count = sum(1 for i in user_interactions if i.emotion_label == "neutral")
    negative_count = sum(1 for i in user_interactions if i.emotion_label == "negative")

    positive_ratio = round(positive_count / total, 2) if total > 0 else 0
    neutral_ratio = round(neutral_count / total, 2) if total > 0 else 0
    negative_ratio = round(negative_count / total, 2) if total > 0 else 0

    # 整体情感趋势
    overall = "positive" if positive_ratio >= 0.5 else ("negative" if negative_ratio > 0.3 else "neutral")

    # 评论高亮（取有标签的所有消息，用户+导游）
    comment_highlights = []
    for i in interactions[:50]:
        if i.emotion_label and i.message:
            comment_highlights.append({
                "comment": i.message[:200],
                "sentiment": i.emotion_label,
                "confidence": round(i.sentiment_score, 2) if i.sentiment_score else 0.5,
                "role": i.role,
                "time": str(i.send_time) if i.send_time else "",
            })

    # 关键词统计（使用1~4字的词组做切分）
    pos_msgs = [i.message for i in user_interactions if i.emotion_label == "positive"]
    neg_msgs = [i.message for i in user_interactions if i.emotion_label == "negative"]
    top_positive_keywords = _get_top_words(pos_msgs, 8)
    top_negative_keywords = _get_top_words(neg_msgs, 8)

    # 热门提问（从用户消息中提取高频短句）
    user_questions = [i.message for i in user_interactions if i.message and len(i.message) > 4]
    hot_questions = _get_top_questions(user_questions, top_n=8)

    # 热门话题分类（基于关键词匹配的用户消息话题分布）
    hot_topics = _extract_hot_topics(
        [i.message for i in user_interactions if i.message], top_n=10
    )

    # 服务建议
    suggestions = []
    if negative_ratio > 0.3:
        suggestions.append("负面反馈占比超过30%，建议优先排查游客集中反映的问题。")
    elif negative_ratio > 0.1:
        suggestions.append("有一定比例负面反馈，建议关注具体负面内容。")
    if positive_ratio >= 0.5:
        suggestions.append("游客整体满意度较高，请继续保持优质服务。")
    if top_negative_keywords:
        suggestions.append(f"负面高频词: {', '.join(top_negative_keywords[:5])}")
    if hot_topics:
        top_topic = hot_topics[0] if hot_topics else {}
        suggestions.append(f"游客最关注「{top_topic.get('topic', '景区')}」类话题，建议丰富相关内容。")
    suggestions.append("定期收集游客反馈，建立持续改进机制。")

    return make_return_data(
        True, ResultCode.SUCCESS, "成功",
        {
            "overall_sentiment": overall,
            "total_interactions": total,
            "positive_count": positive_count,
            "neutral_count": neutral_count,
            "negative_count": negative_count,
            "positive_ratio": positive_ratio,
            "neutral_ratio": neutral_ratio,
            "negative_ratio": negative_ratio,
            "top_positive_keywords": top_positive_keywords,
            "top_negative_keywords": top_negative_keywords,
            "hot_questions": hot_questions,
            "hot_topics": hot_topics,
            "comment_highlights": comment_highlights,
            "suggestions": suggestions,
        },
    )


@router.get("/dashboard/stats", summary="运营数据看板")
async def get_dashboard_stats(user_id: int = Depends(get_current_user_info)):
    """获取核心运营数据（当日/本周）"""
    # 获取服务统计
    service_stats = await get_service_stats(user_id)

    # 获取情感汇总
    sentiment = await get_sentiment_summary(user_id)

    # 获取最近会话
    sessions, total_sessions = await get_db_tour_sessions(user_id, current_page=1, page_size=10)

    # 获取热门问答（最近交互中的Top5问题）
    interactions = await get_visitor_interactions(limit=100)
    user_questions = [i.message for i in interactions if i.role == "user"]
    hot_questions = _get_top_questions(user_questions, top_n=5)

    # 日趋势数据（最近7天 — 从数据库读取真实数据）
    daily_trend = []
    try:
        from ..database.init_db import DB_ENGINE
        from sqlmodel import Session, select, func
        from ..models.tour_models import TourSessionStatus, VisitorInteraction

        today = datetime.now().date()
        week_start = datetime(today.year, today.month, today.day) - timedelta(days=today.weekday())
        with Session(DB_ENGINE) as db:
            for i in range(7):
                day_start = week_start + timedelta(days=i)
                day_end = day_start + timedelta(days=1)
                day_sessions = db.scalar(
                    select(func.count(TourSessionStatus.status_id))
                    .where(TourSessionStatus.start_time >= day_start, TourSessionStatus.start_time < day_end)
                ) or 0
                # 当天满意度
                day_interactions = db.exec(
                    select(VisitorInteraction)
                    .where(VisitorInteraction.send_time >= day_start, VisitorInteraction.send_time < day_end)
                ).all()
                if day_interactions:
                    scores = [it.sentiment_score or 0.5 for it in day_interactions if it.sentiment_score > 0]
                    day_sat = round(sum(scores) / len(scores) * 100, 1) if scores else 0
                else:
                    day_sat = 0
                daily_trend.append({
                    "date": day_start.strftime("%m-%d"),
                    "sessions": day_sessions,
                    "satisfaction": day_sat,
                })
    except Exception:
        # 数据库查询失败时使用空数据
        for i in range(7):
            day = datetime.now() - timedelta(days=6 - i)
            daily_trend.append({
                "date": day.strftime("%m-%d"),
                "sessions": 0,
                "satisfaction": 0,
            })

    return make_return_data(
        True, ResultCode.SUCCESS, "成功",
        {
            "today_sessions": service_stats.get("today_sessions", 0),
            "today_questions": service_stats.get("today_questions", 0),
            "week_sessions": service_stats.get("week_sessions", 0),
            "average_satisfaction": sentiment.get("positive_rate", 0),
            "sentiment_distribution": {
                "positive": sentiment.get("positive", 0),
                "neutral": sentiment.get("neutral", 0),
                "negative": sentiment.get("negative", 0),
            },
            "hot_questions": hot_questions,
            "daily_trend": daily_trend,
            "total_sessions": total_sessions,
        },
    )


@router.get("/feedback/list", summary="游客反馈列表")
async def get_feedback_list(
    currentPage: int = 1,
    pageSize: int = 10,
    user_id: int = Depends(get_current_user_info),
):
    """获取游客反馈记录列表"""
    from ..database.analytics_db import get_feedback_list as get_fb_list

    feedbacks, total = await get_fb_list(user_id, currentPage, pageSize)

    fb_data = []
    for fb in feedbacks:
        fb_data.append({
            "feedback_id": fb.feedback_id,
            "session_id": fb.session_id,
            "overall_score": fb.overall_sentiment_score,
            "emotion_label": fb.overall_emotion_label,
            "topics": json.loads(fb.topics) if fb.topics else [],
            "feedback_text": fb.feedback_text,
            "created_at": str(fb.created_at) if fb.created_at else "",
        })

    return make_return_data(
        True, ResultCode.SUCCESS, "成功",
        {"feedback_list": fb_data, "currentPage": currentPage, "pageSize": pageSize, "totalSize": total},
    )


def _extract_hot_topics(messages: list, top_n: int = 10) -> list:
    """从用户消息中提取热点话题关键词"""
    if not messages:
        return []

    # 常见话题关键词
    topic_keywords = {
        "历史典故": ["历史", "古代", "从前", "故事", "传说", "由来", "起源"],
        "建筑特色": ["建筑", "结构", "风格", "设计", "雕刻", "屋顶"],
        "自然风景": ["风景", "山水", "瀑布", "花", "树", "湖", "山", "自然"],
        "拍照打卡": ["拍照", "打卡", "摄影", "好看", "美", "网红"],
        "门票价格": ["门票", "价格", "多少钱", "收费", "费用", "贵"],
        "开放时间": ["时间", "几点", "开门", "关门", "开放", "营业"],
        "游览路线": ["路线", "怎么走", "多远", "多长时间", "方向"],
        "交通出行": ["车", "公交", "地铁", "停车", "打车", "怎么去"],
        "餐饮美食": ["吃", "餐厅", "美食", "小吃", "喝", "饮料"],
        "住宿休息": ["住", "酒店", "住宿", "休息", "房间"],
        "亲子游玩": ["孩子", "小孩", "亲子", "家庭", "儿童"],
        "文创纪念品": ["纪念品", "文创", "特产", "礼物", "买"],
    }

    topic_counter = Counter()
    for msg in messages:
        for topic, keywords in topic_keywords.items():
            for kw in keywords:
                if kw in msg:
                    topic_counter[topic] += 1
                    break

    return [
        {"topic": topic, "count": count}
        for topic, count in topic_counter.most_common(top_n)
    ]


def _get_top_words(messages: list, top_n: int = 8) -> list:
    """从消息中提取高频词汇"""
    if not messages:
        return []
    all_text = " ".join(messages)
    # 简单方式：按长度过滤出有意义的词（大于1个字）
    words = [w for w in all_text.replace("，", " ").replace("。", " ").replace("？", " ").split() if len(w) >= 2]
    counter = Counter(words)
    return [w for w, _ in counter.most_common(top_n)]


def _get_top_questions(questions: list, top_n: int = 5) -> list:
    """获取最热门的问题"""
    if not questions:
        return []

    # 简单频率统计（去重相似问题）
    counter = Counter()
    for q in questions:
        # 取前20个字符作为问题摘要
        short_q = q[:20] + ("..." if len(q) > 20 else "")
        counter[short_q] += 1

    return [
        {"question": q, "count": c}
        for q, c in counter.most_common(top_n)
    ]


# =======================================================
#   新增：综合数据看板 + 报告生成接口
# =======================================================


@router.get("/comprehensive", summary="综合分析数据看板")
async def get_comprehensive_analytics(user_id: int = Depends(get_current_user_info)):
    """获取综合分析数据：景点排行、问题类型分布、服务趋势、时段分布"""
    from ..database.analytics_db import (
        get_daily_service_trend,
        get_global_emotion_stats,
        get_hot_spot_ranking,
        get_hourly_distribution,
    )

    # 并行获取各维度数据
    spot_ranking = await get_hot_spot_ranking(10)
    daily_trend = await get_daily_service_trend(30)
    hourly_dist = await get_hourly_distribution(7)
    emotion_stats = await get_global_emotion_stats()
    sentiment = await get_sentiment_summary(user_id)
    service_stats = await get_service_stats(user_id)

    return make_return_data(
        True, ResultCode.SUCCESS, "成功",
        {
            "spot_ranking": spot_ranking,
            "daily_trend": daily_trend,
            "hourly_distribution": hourly_dist,
            "emotion_stats": emotion_stats,
            "sentiment": sentiment,
            "service_stats": service_stats,
        },
    )


@router.get("/knowledge-gaps", summary="全局知识盲区分析")
async def get_knowledge_gaps(user_id: int = Depends(get_current_user_info)):
    """从全量对话中挖掘知识盲区"""
    interactions = await get_visitor_interactions(limit=500)

    # 收集所有用户问题和导游回复
    user_questions = [i.message for i in interactions if i.role == "user"]
    guide_responses = [i.message for i in interactions if i.role == "guide"]

    # 高频问题（可能是知识盲区信号）
    from collections import Counter
    import re

    # 提取包含"不知道""不清楚""无法回答"等关键词的问题
    uncertainty_keywords = ["不知道", "不清楚", "无法回答", "没有相关", "抱歉", "暂时没有", "不太了解"]
    uncertain_questions = []
    for i in interactions:
        if i.role == "guide":
            for kw in uncertainty_keywords:
                if kw in (i.message or ""):
                    # 找到对应的用户问题
                    uncertain_questions.append({
                        "guide_response": i.message[:150],
                        "keyword_matched": kw,
                        "time": str(i.send_time) if i.send_time else "",
                    })
                    break

    # 提取问题中的实体词（简单实现：找引号内容或特定模式）
    entity_pattern = re.compile(r'[""]([^""]+)[""]|《([^》]+)》|「([^」]+)」')
    entities = []
    for q in user_questions:
        matches = entity_pattern.findall(q)
        for m in matches:
            entity = m[0] or m[1] or m[2]
            if entity:
                entities.append(entity)

    entity_counter = Counter(entities)

    return make_return_data(
        True, ResultCode.SUCCESS, "成功",
        {
            "uncertain_answers_count": len(uncertain_questions),
            "uncertain_samples": uncertain_questions[:10],
            "top_entities": [
                {"entity": e, "count": c}
                for e, c in entity_counter.most_common(15)
            ],
            "total_interactions_analyzed": len(interactions),
        },
    )


@router.post("/generate-report", summary="AI生成分析报告")
async def generate_analytics_report(
    report_type: str = "daily",  # daily / weekly / session
    session_id: int | None = None,
    user_id: int = Depends(get_current_user_info),
):
    """调用LLM生成结构化分析报告：日报告/周报告/会话报告"""
    from ..routers.llm import get_llm_res

    # 收集报告所需数据
    service_stats = await get_service_stats(user_id)
    sentiment = await get_sentiment_summary(user_id)
    emotion_stats = await get_global_emotion_stats()

    # 获取对话样本用于热题分析
    interactions = await get_visitor_interactions(limit=200)
    user_questions = [i.message for i in interactions if i.role == "user"][:30]

    # 构建数据摘要
    data_summary = f"""## 景区导览运营数据摘要

### 服务统计
- 今日服务人次: {service_stats.get('today_sessions', 0)}
- 今日提问数: {service_stats.get('today_questions', 0)}
- 本周服务人次: {service_stats.get('week_sessions', 0)}

### 情感分析
- 总交互数: {emotion_stats.get('total', 0)}
- 正面情绪占比: {emotion_stats.get('positive_rate', 0)}%
- 负面情绪占比: {emotion_stats.get('negative_rate', 0)}%

### 近期游客提问样本
"""
    for i, q in enumerate(user_questions[:10], 1):
        data_summary += f"{i}. {q[:100]}\n"

    # 根据报告类型构建prompt
    type_labels = {"daily": "日报", "weekly": "周报", "session": "会话报告"}
    report_label = type_labels.get(report_type, "分析报告")

    report_prompt = [
        {"role": "system", "content": (
            f"你是一个景区智能导览系统的数据分析专家。请根据提供的运营数据，生成一份{report_label}。\n"
            "回复格式为JSON：\n"
            '{\n'
            '  "title": "报告标题",\n'
            '  "period": "统计周期(如2026-07-12 日报)",\n'
            '  "executive_summary": "核心摘要(2-3句话)",\n'
            '  "key_metrics": [\n'
            '    {"name": "指标名", "value": "数值", "trend": "up/down/stable", "comment": "解读"}\n'
            '  ],\n'
            '  "sentiment_analysis": {\n'
            '    "overall": "整体情感结论",\n'
            '    "highlights": ["正面发现1", "正面发现2"],\n'
            '    "concerns": ["需要关注的问题1"]\n'
            '  },\n'
            '  "hot_topics": ["热门话题1", "热门话题2", "热门话题3"],\n'
            '  "service_insights": {\n'
            '    "strengths": ["优势1", "优势2"],\n'
            '    "weaknesses": ["待改进1", "待改进2"]\n'
            '  },\n'
            '  "recommendations": [\n'
            '    {"priority": "高/中/低", "action": "具体行动建议", "expected_impact": "预期效果"}\n'
            '  ],\n'
            '  "next_steps": "下一步工作建议(1-2句话)"\n'
            '}\n'
            "只输出JSON，不要其他内容。"
        )},
        {"role": "user", "content": f"请根据以下数据生成{report_label}：\n\n{data_summary}"},
    ]

    try:
        logger.info(f"[GenerateReport] Generating {report_type} report for user {user_id}")
        response = await get_llm_res(report_prompt)
        logger.info(f"[GenerateReport] LLM response length: {len(response)}")

        import json
        import re

        def _extract_json(text: str) -> dict:
            """从LLM响应中健壮地提取JSON"""
            text = text.strip()
            # 去掉 markdown 代码块
            if text.startswith("```"):
                parts = text.split("```", 2)
                if len(parts) >= 2:
                    text = parts[1]
                    if text.startswith("json") or text.startswith("JSON"):
                        text = text[4:]
                    text = text.strip()
            # 找最外层 { } 配对（用计数器，避免贪婪匹配吃掉嵌套对象后的无关文本）
            start = text.find("{")
            if start == -1:
                raise ValueError("No JSON object found in response")
            depth = 0
            end = start
            for i in range(start, len(text)):
                if text[i] == "{":
                    depth += 1
                elif text[i] == "}":
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        break
            return json.loads(text[start:end])

        result = _extract_json(response)

        # 保存报告
        from ..database.analytics_db import save_analytics_report
        report_id = await save_analytics_report(report_type, json.dumps(result, ensure_ascii=False), user_id)

        return make_return_data(True, ResultCode.SUCCESS, "报告生成成功", {
            "report_id": report_id,
            "report_type": report_type,
            "report": result,
            "generated_at": str(datetime.now()),
        })
    except json.JSONDecodeError as e:
        logger.error(f"[GenerateReport] JSON parse failed: {e}\nRaw response: {response[:500]}")
        return make_return_data(False, ResultCode.FAIL, f"AI返回格式异常，请重试。详情: {str(e)[:100]}", "")
    except Exception as e:
        logger.error(f"[GenerateReport] Failed: {type(e).__name__}: {e}")
        return make_return_data(False, ResultCode.FAIL, f"报告生成失败: {str(e)[:150]}", "")


@router.get("/reports", summary="获取历史分析报告列表")
async def get_reports(
    report_type: str | None = None,
    limit: int = 20,
    user_id: int = Depends(get_current_user_info),
):
    """获取之前生成的分析报告"""
    from ..database.analytics_db import get_analytics_reports

    reports = await get_analytics_reports(report_type, limit)
    return make_return_data(True, ResultCode.SUCCESS, "成功", {"reports": reports})


@router.get("/visitor-profile/{sessionId}", summary="获取游客画像")
async def get_visitor_profile(sessionId: int, user_id: int = Depends(get_current_user_info)):
    """获取单个会话的游客画像：兴趣标签、活跃度、满意度趋势"""
    from ..database.tour_session_db import get_conversation_history
    from ..modules.sentiment_analyzer import (
        analyze_visitor_engagement,
        extract_visitor_interests,
    )

    conversation = await get_conversation_history(sessionId)
    if not conversation:
        return make_return_data(False, ResultCode.FAIL, "该会话无对话记录", "")

    user_messages = [m.get("message", "") for m in conversation if m.get("role") == "user"]
    interests = extract_visitor_interests(user_messages)
    engagement = analyze_visitor_engagement(conversation)

    # 获取情感趋势
    from ..database.analytics_db import get_visitor_interactions
    interactions = await get_visitor_interactions(session_id=sessionId, limit=200)
    from ..modules.sentiment_analyzer import get_emotion_trend_analysis
    emotion_trend = get_emotion_trend_analysis(interactions)

    # 意图分类统计
    from collections import Counter
    from ..modules.sentiment_analyzer import classify_question_intent
    intents = [classify_question_intent(msg) for msg in user_messages]
    intent_counter = Counter(intents)

    return make_return_data(
        True, ResultCode.SUCCESS, "成功",
        {
            "session_id": sessionId,
            "interests": [
                {"category": k, "score": v}
                for k, v in list(interests.items())[:5]
            ],
            "engagement": engagement,
            "emotion_trend": emotion_trend,
            "intent_distribution": [
                {"intent": intent, "count": count}
                for intent, count in intent_counter.most_common(8)
            ],
            "top_questions": user_messages[:5],
        },
    )


@router.get("/visitor-segments", summary="游客群体细分")
async def get_visitor_segments(user_id: int = Depends(get_current_user_info)):
    """基于所有会话数据的游客群体细分"""
    from ..database.init_db import DB_ENGINE
    from sqlmodel import Session as DBSession, select
    from ..models.tour_models import TourSessionInfo, VisitorInteraction

    with DBSession(DB_ENGINE) as session:
        # 获取所有非删除的会话
        all_sessions = session.exec(
            select(TourSessionInfo).where(TourSessionInfo.delete == False)
        ).all()

        segments = {
            "历史文化爱好者": 0,
            "自然风光爱好者": 0,
            "摄影打卡型": 0,
            "亲子家庭型": 0,
            "综合体验型": 0,
        }

        segment_keywords = {
            "历史文化爱好者": ["历史", "文化", "古代", "故事", "传说", "古迹"],
            "自然风光爱好者": ["风景", "自然", "山水", "花", "瀑布"],
            "摄影打卡型": ["拍照", "打卡", "摄影", "好看", "网红"],
            "亲子家庭型": ["孩子", "小孩", "亲子", "家庭"],
        }

        for s in all_sessions:
            preferences = s.visitor_preferences or ""
            classified = False
            for seg, keywords in segment_keywords.items():
                if any(kw in preferences for kw in keywords):
                    segments[seg] += 1
                    classified = True
                    break
            if not classified:
                segments["综合体验型"] += 1

        # 计算百分比
        total = max(sum(segments.values()), 1)
        segment_data = [
            {"segment": name, "count": count, "percentage": round(count / total * 100, 1)}
            for name, count in segments.items()
        ]

        return make_return_data(True, ResultCode.SUCCESS, "成功", {
            "segments": segment_data,
            "total_sessions": total,
        })


def _generate_suggestions(sentiment_summary: dict, hot_topics: list) -> list:
    """根据情感分析和热点话题生成服务建议"""
    suggestions = []

    total = sentiment_summary.get("total", 0)
    if total == 0:
        return ["暂无足够的交互数据，建议积累更多游客反馈后再进行分析。"]

    negative_rate = sentiment_summary.get("negative", 0) / total * 100 if total > 0 else 0
    positive_rate = sentiment_summary.get("positive_rate", 0)

    if negative_rate > 20:
        suggestions.append("⚠️ 游客负面反馈比例较高（{:.0f}%），建议检查服务质量并针对性改进。".format(negative_rate))

    if positive_rate >= 80:
        suggestions.append("✅ 游客整体满意度较高（{:.1f}%），请继续保持优质服务。".format(positive_rate))

    # 基于热点话题的建议
    topic_dict = {t["topic"]: t["count"] for t in hot_topics} if hot_topics else {}

    if topic_dict.get("门票价格", 0) > 5:
        suggestions.append("💡 游客对门票价格关注度较高，建议在知识库中补充详细的价格政策和优惠政策说明。")

    if topic_dict.get("游览路线", 0) > 5:
        suggestions.append("💡 游客频繁询问游览路线，建议优化路线推荐功能或在关键位置增设导览标识。")

    if topic_dict.get("拍照打卡", 0) > 3:
        suggestions.append("📸 拍照打卡是游客热门需求，建议在景点介绍中标注最佳拍照点和时间。")

    if not suggestions:
        suggestions.append("📊 当前数据量较小，尚未形成显著的服务建议。持续积累后可提供更精准的分析。")

    return suggestions
