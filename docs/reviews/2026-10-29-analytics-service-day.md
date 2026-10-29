# 运营看板“今日提问”凌晨归零：改为服务日统计

反馈：“今天明明提问了，你加载一下啊”，配图为管理端首页“今日提问 0”。

## 加载到的真实数据

数据库 `visitor_interaction` 中当天确实有 11 条游客提问，时间全部落在 2026-10-28 22:08–23:34（如 22:08“仁寿殿有什么拍照建议？”、23:34“介绍长廊”）。反馈时本地时间已是 2026-10-29 00:42。

旧口径用自然日：`func.date(send_time) == datetime.now().date()`。跨过 0 点后“今日”变成 10-29，前一晚的提问被排除，看板显示 0；`/analytics/comprehensive` 与 `/dashboard` 均返回 0，不是前端缓存或接口没刷新。

## 修复

- 新增 `server/base/modules/analytics_time.py`：按可配置的服务日计算“今日/本周”，默认本地 06:00 换日，`ANALYTICS_DAY_START_HOUR` 可设为 0 恢复自然日。
- `get_service_stats` 改用服务日窗口统计提问和会话；顺带修正原来 `today_sessions`/`week_sessions` 完全没按时间过滤（两者都等于全部未删除会话）的问题。
- `/dashboard` 的今日会话、今日提问、本周趋势同步使用服务日口径。
- 管理端首页和分析页的“今日提问”副标题改为“服务日 06:00 起”，中英文文案同步。

## 验证

- `python -m unittest server.tests.test_analytics_time`：5 项通过（凌晨归属前一服务日、06:00 换日、周一服务周、小时配置为 0、非法配置回退）。
- 既有 `test_guide_tts`、`test_rag_runtime`、`test_system_status` 全部通过。
- 重启后端后实测：`/dashboard` 返回 `todayQuestions: 11`、`todaySessions: 20`、`weekSessions: 24`；`/analytics/comprehensive` 返回 `today_questions: 11`。
- `frontend` 的 `type-check` 仅剩既有错误 `KnowledgeUpload.spec.ts`；`i18n` 测试 5 项通过。Vite 已热更新，页面刷新即可看到新口径。

## 备注

- 服务站网页咨询的问题暂存在 `station_visit.messages`，结束/过期时会清空，也不会写入 `visitor_interaction`，因此目前不计入“今日提问”。本次未改该行为，如需统一统计需单独设计持久化。
