from collections import Counter
from typing import Any


def _text_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        text = str(item).strip()
        if text and text not in result:
            result.append(text)
    return result


def _normalized_question(text: str) -> str:
    return "".join(text.strip().rstrip("？?！!。.").split())


def _topic_labels(questions: list[str]) -> list[str]:
    text = " ".join(questions)
    categories = {
        "历史文化与典故": ("历史", "故事", "典故", "由来", "人物"),
        "摄影与打卡": ("拍照", "摄影", "机位", "取景", "打卡"),
        "服务设施": ("服务", "设施", "卫生间", "休息", "餐饮", "小卖部", "母婴"),
        "路线与下一站": ("路线", "下一站", "怎么走", "推荐", "多久"),
        "建筑与园林": ("建筑", "彩画", "长廊", "宫殿", "园林"),
    }
    topics = [name for name, keywords in categories.items() if any(keyword in text for keyword in keywords)]
    return topics[:5] or ["景点综合讲解"]


def normalize_issue_analysis(
    raw: dict[str, Any],
    conversation: list[dict[str, Any]],
    analysis_source: str = "AI语义分析",
) -> dict[str, Any]:
    """把问题挖掘结果规范成前端始终可渲染的完整结构。"""
    questions = [
        str(item.get("message", "")).strip()
        for item in conversation
        if item.get("role") == "user" and str(item.get("message", "")).strip()
    ]
    normalized_to_original: dict[str, str] = {}
    normalized_questions: list[str] = []
    for question in questions:
        normalized = _normalized_question(question)
        if normalized:
            normalized_questions.append(normalized)
            normalized_to_original.setdefault(normalized, question)
    repeated = [
        normalized_to_original[text]
        for text, count in Counter(normalized_questions).items()
        if count > 1
    ]
    topics = _text_list(raw.get("hot_topics")) or _topic_labels(questions)

    knowledge_gaps = _text_list(raw.get("knowledge_gaps"))
    if not knowledge_gaps:
        if any("设施" in question or "卫生间" in question for question in questions):
            knowledge_gaps.append("服务设施的准确位置、距离、开放时间与实时状态仍需补充。")
        if any("拍照" in question or "摄影" in question for question in questions):
            knowledge_gaps.append("拍摄机位与当前光线、人流、构图方式之间的适配信息不够细化。")
        if any("历史" in question or "故事" in question or "典故" in question for question in questions):
            knowledge_gaps.append("代表性历史故事、人物典故及其资料来源仍可继续丰富。")
        if not knowledge_gaps:
            knowledge_gaps.append("现有问答覆盖基础导览需求，但深层追问所需的结构化知识仍需扩充。")

    common_confusions = _text_list(raw.get("common_confusions"))
    if not common_confusions:
        common_confusions.extend(
            f"游客重复询问“{question[:36]}”，说明首次回答的针对性或可执行性不足。"
            for question in repeated[:3]
        )
        if not common_confusions:
            common_confusions.append("游客未出现明显重复追问，仍应关注复合问题中的核心诉求是否被完整回答。")

    service_gaps = _text_list(raw.get("service_gaps"))
    if not service_gaps:
        service_gaps = [
            "缺少将设施位置、步行距离和路线指引整合为可直接执行的地图卡片。",
            "对话上下文与当前景点状态需要持续校验，避免回答内容与游客位置不一致。",
        ]

    improvement_actions = _text_list(raw.get("improvement_actions"))
    if not improvement_actions:
        improvement_actions = [
            "补充景点典故、服务设施坐标、开放时间和无障碍信息等结构化知识。",
            "识别重复追问并重新组织答案，优先给出位置、距离和下一步操作。",
            "结合当前景点和会话上下文校验回答，减少泛化描述与地点漂移。",
        ]

    satisfaction = str(raw.get("satisfaction", "")).strip()
    if satisfaction not in {"高", "中", "低"}:
        satisfaction = "低" if repeated else "中"
    satisfaction_reason = str(raw.get("satisfaction_reason", "")).strip()
    if not satisfaction_reason:
        satisfaction_reason = (
            f"会话中出现{len(repeated)}类重复追问，说明部分核心需求未在首轮得到有效解决。"
            if repeated
            else "会话能够完成基础导览问答，但仍需从准确性、可执行性和知识深度继续优化。"
        )

    summary = str(raw.get("summary", "")).strip()
    if not summary or summary.startswith("{"):
        summary = (
            f"本次共分析{len(questions)}条游客提问，关注点主要集中在{'、'.join(topics[:3])}。"
            f"识别到{len(knowledge_gaps)}项知识盲区和{len(service_gaps)}项服务缺口，"
            "建议优先补充结构化景区数据，并增强上下文校验与重复问题处理能力。"
        )

    return {
        "knowledge_gaps": knowledge_gaps[:6],
        "common_confusions": common_confusions[:6],
        "service_gaps": service_gaps[:6],
        "satisfaction": satisfaction,
        "satisfaction_reason": satisfaction_reason,
        "hot_topics": topics[:6],
        "improvement_actions": improvement_actions[:6],
        "summary": summary,
        "analysis_source": analysis_source,
        "analyzed_question_count": len(questions),
    }
