import re


def strip_repeated_name_prefixes(text: str, *names: str) -> str:
    """移除正文段首重复输出的游客或导游姓名，UI 已单独展示说话人。"""
    escaped_names = [re.escape(name.strip()) for name in names if name and name.strip()]
    if not text or not escaped_names:
        return text.strip()
    prefix_pattern = re.compile(
        rf"(?m)^(\s*)(?:{'|'.join(escaped_names)})(?:先生|女士|老师|小朋友)?\s*[，,：:、]\s*"
    )
    return prefix_pattern.sub(r"\1", text).strip()
