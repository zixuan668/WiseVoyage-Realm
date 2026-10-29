#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""运营看板的时间口径。

景区服务常常跨过自然日零点：管理员在凌晨查看看板时，前一晚 22:00 之后的
提问和会话仍属于同一个服务日。这里统一按可配置的服务日计算“今日/本周”，
默认从本地时间 06:00 换日，可用 ANALYTICS_DAY_START_HOUR 调整（0 即自然日）。
"""

import os
from datetime import datetime, timedelta

DEFAULT_DAY_START_HOUR = 6


def day_start_hour() -> int:
    """读取服务日起始小时；非法配置回退到默认值。"""
    try:
        hour = int(os.getenv("ANALYTICS_DAY_START_HOUR", str(DEFAULT_DAY_START_HOUR)))
    except (TypeError, ValueError):
        return DEFAULT_DAY_START_HOUR
    return hour if 0 <= hour <= 23 else DEFAULT_DAY_START_HOUR


def service_day_window(now: datetime | None = None) -> tuple[datetime, datetime]:
    """返回当前服务日的 [起始, 结束) 时间。"""
    current = now or datetime.now()
    hour = day_start_hour()
    start = datetime(current.year, current.month, current.day, hour)
    if current < start:
        start -= timedelta(days=1)
    return start, start + timedelta(days=1)


def service_week_window(now: datetime | None = None) -> tuple[datetime, datetime]:
    """返回当前服务周（周一开始）的 [起始, 结束) 时间。"""
    day_start, day_end = service_day_window(now)
    week_start = day_start - timedelta(days=day_start.weekday())
    return week_start, day_end
