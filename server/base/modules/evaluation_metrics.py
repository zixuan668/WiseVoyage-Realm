"""可复用的知识问答评测指标。

该模块只负责可解释的关键词覆盖判定，不把关键词命中率包装成语义正确率。
"""

from __future__ import annotations

import math
import re
import unicodedata
from typing import Iterable


KEYWORD_SPLIT_PATTERN = re.compile(r"[,，。；;、\s]+")


def parse_expected_keywords(value: str | Iterable[str]) -> list[str]:
    """将题库中的逗号分隔关键词转换为去重列表。"""
    if isinstance(value, str):
        candidates = KEYWORD_SPLIT_PATTERN.split(value)
    else:
        candidates = list(value)

    result: list[str] = []
    for candidate in candidates:
        keyword = str(candidate).strip()
        if keyword and keyword not in result:
            result.append(keyword)
    return result


def normalize_text(value: str) -> str:
    """统一全半角、大小写和空白，保留数字与中文语义。"""
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", value).lower())


def keyword_is_present(keyword: str, actual_answer: str) -> bool:
    normalized_keyword = normalize_text(keyword)
    normalized_answer = normalize_text(actual_answer)

    # 纯数字关键词使用数字边界，避免“3”错误命中“30”。
    if re.fullmatch(r"\d+(?:\.\d+)?", normalized_keyword):
        return bool(
            re.search(
                rf"(?<![\d.]){re.escape(normalized_keyword)}(?![\d.])",
                normalized_answer,
            )
        )
    return normalized_keyword in normalized_answer


def evaluate_keyword_coverage(
    expected_keywords: str | Iterable[str],
    actual_answer: str,
    *,
    minimum_ratio: float = 0.30,
    maximum_required: int = 3,
) -> dict:
    """返回透明的关键词覆盖指标及是否达到单题阈值。"""
    keywords = parse_expected_keywords(expected_keywords)
    if not keywords or not actual_answer:
        return {
            "keywords": keywords,
            "matched_keywords": [],
            "matched_count": 0,
            "required_count": 0 if not keywords else 1,
            "coverage": 0.0,
            "is_correct": False,
        }

    matched_keywords = [
        keyword for keyword in keywords if keyword_is_present(keyword, actual_answer)
    ]
    required_count = max(
        1,
        min(maximum_required, math.ceil(len(keywords) * minimum_ratio)),
    )
    return {
        "keywords": keywords,
        "matched_keywords": matched_keywords,
        "matched_count": len(matched_keywords),
        "required_count": required_count,
        "coverage": round(len(matched_keywords) / len(keywords) * 100, 1),
        "is_correct": len(matched_keywords) >= required_count,
    }
