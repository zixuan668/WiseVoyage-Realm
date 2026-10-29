"""运营看板“今日/本周”按服务日统计，凌晨跨零点不清零。"""
import os
import unittest
from datetime import datetime
from unittest.mock import patch

from server.base.modules.analytics_time import (
    DEFAULT_DAY_START_HOUR,
    day_start_hour,
    service_day_window,
    service_week_window,
)


class ServiceDayWindowTests(unittest.TestCase):
    def test_before_six_belongs_to_previous_service_day(self):
        start, end = service_day_window(datetime(2026, 10, 29, 0, 42))
        self.assertEqual(start, datetime(2026, 10, 28, 6, 0))
        self.assertEqual(end, datetime(2026, 10, 29, 6, 0))

    def test_after_six_belongs_to_current_service_day(self):
        start, end = service_day_window(datetime(2026, 10, 29, 6, 0))
        self.assertEqual(start, datetime(2026, 10, 29, 6, 0))
        self.assertEqual(end, datetime(2026, 10, 30, 6, 0))

    def test_week_starts_on_monday_service_day(self):
        start, end = service_week_window(datetime(2026, 10, 29, 0, 42))
        self.assertEqual(start, datetime(2026, 10, 26, 6, 0))
        self.assertEqual(end, datetime(2026, 10, 29, 6, 0))

    def test_zero_hour_keeps_calendar_day(self):
        with patch.dict(os.environ, {"ANALYTICS_DAY_START_HOUR": "0"}):
            start, end = service_day_window(datetime(2026, 10, 29, 0, 42))
        self.assertEqual(start, datetime(2026, 10, 29, 0, 0))
        self.assertEqual(end, datetime(2026, 10, 30, 0, 0))

    def test_invalid_hour_falls_back_to_default(self):
        for value in ("", "abc", "-1", "24"):
            with patch.dict(os.environ, {"ANALYTICS_DAY_START_HOUR": value}):
                self.assertEqual(day_start_hour(), DEFAULT_DAY_START_HOUR)


if __name__ == "__main__":
    unittest.main()
