from collections import Counter
from typing import Any


def _text_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _infer_interests(messages: list[str]) -> list[str]:
    text = " ".join(messages)
    categories = {
        "历史文化": ("历史", "故事", "典故", "古建", "建筑"),
        "摄影打卡": ("拍照", "摄影", "机位", "取景"),
        "服务设施": ("服务", "卫生间", "休息", "餐饮", "设施"),
        "路线规划": ("路线", "下一站", "怎么走", "推荐"),
        "自然景观": ("风景", "湖", "山", "自然"),
    }
    return [name for name, keywords in categories.items() if any(keyword in text for keyword in keywords)][:4]


def normalize_session_report(raw: dict[str, Any], conversation: list[dict[str, Any]]) -> dict[str, Any]:
    """将模型输出约束为前端可稳定渲染的完整报告结构。"""
    user_messages = [str(item.get("message", "")) for item in conversation if item.get("role") == "user"]
    guide_messages = [str(item.get("message", "")) for item in conversation if item.get("role") == "guide"]
    avg_response_length = round(sum(map(len, guide_messages)) / max(len(guide_messages), 1))

    try:
        score = int(float(raw.get("session_quality_score", 0)))
    except (TypeError, ValueError):
        score = 0
    if score <= 0:
        score = min(88, 62 + min(len(user_messages), 6) * 3 + (6 if avg_response_length >= 100 else 0))
    score = max(0, min(100, score))
    default_level = "优秀" if score >= 90 else "良好" if score >= 75 else "一般" if score >= 60 else "较差"
    quality_level = str(raw.get("quality_level", "")).strip()
    if quality_level not in {"优秀", "良好", "一般", "较差"}:
        quality_level = default_level

    profile = raw.get("visitor_profile") if isinstance(raw.get("visitor_profile"), dict) else {}
    interests = _text_list(profile.get("interests")) or _infer_interests(user_messages) or ["综合导览"]
    engagement = str(profile.get("engagement_level", "")).strip()
    if engagement not in {"高", "中", "低"}:
        engagement = "高" if len(user_messages) >= 5 else "中" if len(user_messages) >= 2 else "低"
    trend = str(profile.get("satisfaction_trend", "")).strip()
    if trend not in {"上升", "平稳", "下降"}:
        trend = "平稳"

    qa_summary = raw.get("qa_summary") if isinstance(raw.get("qa_summary"), dict) else {}
    try:
        deep_ratio = float(qa_summary.get("deep_questions_ratio", 0))
    except (TypeError, ValueError):
        deep_ratio = 0.0
    deep_ratio = max(0.0, min(1.0, deep_ratio))

    highlights = _text_list(raw.get("service_highlights"))
    if not highlights:
        highlights = [
            "能够围绕游客提问提供景点背景与可执行的游览建议。",
            "对话覆盖当前景点、拍摄建议和路线衔接等导览场景。",
        ]

    gaps = _text_list(raw.get("knowledge_gaps"))
    repeated = [question for question, count in Counter(user_messages).items() if count > 1]
    if not gaps:
        gaps = ["服务设施的精确位置、开放时间和实时状态仍需补充结构化数据。"]
        if repeated:
            gaps.append(f"游客重复询问“{repeated[0][:28]}”，说明首次回答的针对性仍需提升。")
        else:
            gaps.append("景点典故、建筑细节及资料来源可继续丰富，以支撑更深入追问。")

    suggestions: list[dict[str, str]] = []
    raw_suggestions = raw.get("improvement_suggestions")
    if isinstance(raw_suggestions, list):
        for item in raw_suggestions:
            if not isinstance(item, dict):
                continue
            suggestion = str(item.get("suggestion", "")).strip()
            if suggestion:
                priority = str(item.get("priority", "中")).strip()
                suggestions.append({
                    "area": str(item.get("area", "服务优化")).strip() or "服务优化",
                    "suggestion": suggestion,
                    "priority": priority if priority in {"高", "中", "低"} else "中",
                })
    if not suggestions:
        suggestions = [
            {"area": "知识库", "suggestion": "补充景点典故、设施位置、开放时间及无障碍信息。", "priority": "高"},
            {"area": "交互体验", "suggestion": "对重复问题优先给出更直接、具体且可执行的答案。", "priority": "中"},
        ]

    summary = str(raw.get("executive_summary", "")).strip()
    if not summary or summary.startswith("{"):
        summary = (
            f"本次导览共完成{len(user_messages)}轮游客提问，整体服务质量为{quality_level}。"
            "回答能够覆盖主要游览需求，但仍应继续补充知识细节和设施数据，提升首轮回答的针对性。"
        )

    return {
        "session_quality_score": score,
        "quality_level": quality_level,
        "visitor_profile": {
            "interests": interests,
            "engagement_level": engagement,
            "satisfaction_trend": trend,
        },
        "qa_summary": {
            "total_exchanges": len(user_messages),
            "deep_questions_ratio": deep_ratio,
            "avg_response_length": avg_response_length,
        },
        "knowledge_gaps": gaps[:6],
        "service_highlights": highlights[:6],
        "improvement_suggestions": suggestions[:6],
        "executive_summary": summary,
    }
