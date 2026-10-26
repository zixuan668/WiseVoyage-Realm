#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    :   sentiment_analyzer.py
@Time    :   2026/06/10
@Project :   景区导览AI数字人
@Desc    :   游客情感分析模块 — 分析游客交互消息的情感倾向
"""

import os
from typing import Tuple

from loguru import logger


# 情感关键词词典
POSITIVE_KEYWORDS = [
    "好", "棒", "美", "漂亮", "喜欢", "爱", "感谢", "谢谢", "太",
    "不错", "赞", "厉害", "牛", "开心", "高兴", "满意", "推荐",
    "值得", "有趣", "精彩", "震撼", "壮观", "惊艳", "感动", "温暖",
    "great", "wonderful", "beautiful", "amazing", "love",
]

NEGATIVE_KEYWORDS = [
    "不好", "差", "失望", "无聊", "没意思", "烂", "糟糕", "坑",
    "不推荐", "骗", "贵", "讨厌", "烦", "生气", "难过", "可惜",
    "后悔", "浪费时间", "听不懂", "不清楚", "错误", "不对",
    "bad", "terrible", "boring", "disappointing",
]


def keyword_sentiment_analyze(text: str) -> Tuple[float, str]:
    """基于关键词的情感分析

    Args:
        text: 待分析文本

    Returns:
        Tuple[float, str]: (情感分数 0~1, 情感标签)
    """
    if not text:
        return 0.5, "neutral"

    positive_count = sum(1 for kw in POSITIVE_KEYWORDS if kw in text)
    negative_count = sum(1 for kw in NEGATIVE_KEYWORDS if kw in text)

    if positive_count > negative_count:
        score = min(0.5 + (positive_count - negative_count) * 0.15, 1.0)
        label = "positive"
    elif negative_count > positive_count:
        score = max(0.5 - (negative_count - positive_count) * 0.15, 0.0)
        label = "negative"
    else:
        score = 0.5
        label = "neutral"

    return round(score, 2), label


async def llm_sentiment_analyze(text: str) -> Tuple[float, str]:
    """基于LLM的情感分析（更准确但更慢）

    Args:
        text: 待分析文本

    Returns:
        Tuple[float, str]: (情感分数 0~1, 情感标签)
    """
    try:
        from ..utils import LLM_MODEL_HANDLER

        model_name = os.getenv("LLM_MODEL_NAME", "Qwen/Qwen2.5-7B-Instruct")

        prompt = [
            {
                "role": "system",
                "content": (
                    "你是一个情感分析专家。请分析以下游客消息的情感倾向。"
                    '只返回JSON格式：{"score": 0.0~1.0, "label": "positive/neutral/negative"}'
                    "其中1.0表示非常正面，0.0表示非常负面。"
                ),
            },
            {"role": "user", "content": f"请分析情感：{text}"},
        ]

        import asyncio

        response = await asyncio.to_thread(
            LLM_MODEL_HANDLER.chat.completions.create,
            model=model_name,
            messages=prompt,
            stream=False,
            temperature=0.1,
            max_tokens=256,
        )
        import json

        raw = (response.choices[0].message.content or "").strip()
        if raw.startswith("```"):
            raw = raw.split("```", 2)[1].removeprefix("json").strip()
        result = json.loads(raw)
        return float(result.get("score", 0.5)), str(result.get("label", "neutral"))
    except Exception as e:
        logger.warning(f"LLM sentiment analysis failed, falling back to keyword: {e}")
        return keyword_sentiment_analyze(text)


async def analyze_sentiment(text: str, use_llm: bool = False) -> Tuple[float, str]:
    """分析文本情感（入口函数）

    Args:
        text: 待分析文本
        use_llm: 是否使用LLM分析（默认使用关键词方式）

    Returns:
        Tuple[float, str]: (情感分数, 情感标签)
    """
    if use_llm:
        return await llm_sentiment_analyze(text)
    return keyword_sentiment_analyze(text)


# =======================================================
#   新增：游客画像与行为分析
# =======================================================

# 兴趣关键词映射
INTEREST_KEYWORDS = {
    "历史文化": ["历史", "古代", "从前", "故事", "传说", "由来", "起源", "文化", "古迹", "传统", "朝代"],
    "自然风光": ["自然", "风景", "山水", "风光", "花", "树", "瀑布", "山", "湖", "植物", "生态"],
    "建筑艺术": ["建筑", "结构", "风格", "设计", "雕刻", "屋顶", "园林", "寺庙", "塔"],
    "拍照打卡": ["拍照", "打卡", "摄影", "照片", "好看", "美", "网红", "拍"],
    "美食餐饮": ["吃", "餐厅", "美食", "小吃", "喝", "饮料", "特产", "好吃"],
    "亲子家庭": ["孩子", "小孩", "亲子", "家庭", "带娃", "小朋友", "儿童"],
    "交通出行": ["车", "公交", "地铁", "停车", "打车", "怎么去", "交通", "路线"],
    "购物纪念": ["纪念品", "文创", "礼物", "买", "商店", "购物", "特产"],
    "住宿休息": ["住", "酒店", "住宿", "休息", "房间", "民宿"],
    "门票价格": ["门票", "价格", "多少钱", "收费", "费用", "优惠"],
}


def extract_visitor_interests(user_messages: list) -> dict:
    """从游客消息中提取兴趣标签

    Args:
        user_messages: 游客消息列表

    Returns:
        dict: {兴趣标签: 提及次数}，按次数降序排列
    """
    if not user_messages:
        return {}

    all_text = " ".join(user_messages)
    interest_scores = {}

    for category, keywords in INTEREST_KEYWORDS.items():
        score = 0
        for kw in keywords:
            score += all_text.count(kw)
        if score > 0:
            interest_scores[category] = score

    # 按分数降序排列
    return dict(sorted(interest_scores.items(), key=lambda x: x[1], reverse=True))


def classify_question_intent(text: str) -> str:
    """基于关键词的问题意图分类

    Args:
        text: 待分类文本

    Returns:
        str: 意图类型
    """
    intent_map = {
        "历史文化": ["历史", "文化", "古代", "故事", "传说", "由来", "起源"],
        "自然风景": ["风景", "自然", "山水", "花", "树", "瀑布", "山", "湖"],
        "路线指引": ["怎么走", "多远", "多长时间", "方向", "路线", "在哪", "哪里有"],
        "门票价格": ["门票", "价格", "多少钱", "收费", "费用", "贵不贵"],
        "拍照打卡": ["拍照", "打卡", "摄影", "好看", "网红", "照片"],
        "餐饮住宿": ["吃", "餐厅", "酒店", "住宿", "住", "喝"],
        "开放时间": ["时间", "几点", "开门", "关门", "开放", "营业"],
        "设施服务": ["洗手间", "厕所", "停车场", "wifi", "轮椅", "寄存"],
    }

    for intent, keywords in intent_map.items():
        for kw in keywords:
            if kw in text:
                return intent

    return "其他"


def analyze_visitor_engagement(interactions: list) -> dict:
    """分析游客参与度

    Args:
        interactions: VisitorInteraction列表

    Returns:
        dict: {total_messages, questions_count, avg_question_length, engagement_level}
    """
    if not interactions:
        return {"total_messages": 0, "questions_count": 0, "avg_question_length": 0, "engagement_level": "低"}

    questions = [i for i in interactions if (hasattr(i, "role") and i.role == "user") or i.get("role") == "user"]
    total = len(interactions)
    q_count = len(questions)
    avg_len = sum(len(i.message if hasattr(i, "message") else i.get("message", "")) for i in questions) / max(q_count, 1)

    # 参与度判定
    if q_count >= 10 and avg_len >= 20:
        level = "高"
    elif q_count >= 5:
        level = "中"
    else:
        level = "低"

    return {
        "total_messages": total,
        "questions_count": q_count,
        "avg_question_length": round(avg_len, 1),
        "engagement_level": level,
    }


def get_emotion_trend_analysis(interactions: list) -> dict:
    """分析多轮对话的情感趋势

    Args:
        interactions: VisitorInteraction列表或dict列表

    Returns:
        dict: 情感趋势分析结果
    """
    if not interactions:
        return {"trend": "stable", "overall_score": 0.5, "overall_label": "neutral"}

    scores = []
    for item in interactions:
        score = item.sentiment_score if hasattr(item, "sentiment_score") else item.get("sentiment_score", 0.5)
        scores.append(score)

    if not scores:
        return {"trend": "stable", "overall_score": 0.5, "overall_label": "neutral"}

    avg_score = sum(scores) / len(scores)

    # 趋势判断
    if len(scores) >= 3:
        first_half = sum(scores[: len(scores) // 2]) / (len(scores) // 2)
        second_half = sum(scores[len(scores) // 2 :]) / (len(scores) - len(scores) // 2)
        if second_half > first_half + 0.1:
            trend = "improving"  # 上升
        elif second_half < first_half - 0.1:
            trend = "declining"  # 下降
        else:
            trend = "stable"  # 平稳
    else:
        trend = "stable"

    label = "positive" if avg_score >= 0.6 else ("negative" if avg_score <= 0.4 else "neutral")

    return {
        "trend": trend,
        "overall_score": round(avg_score, 2),
        "overall_label": label,
    }
