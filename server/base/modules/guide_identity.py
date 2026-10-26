"""数字导游声线规则。"""

SHOWCASE_GUIDE_NAME = "小颐"


def resolve_guide_voice(voice_style: str) -> str:
    """返回管理员显式配置的备用声线；未配置时给出女性默认值。"""
    return voice_style or "female_wenrou"
