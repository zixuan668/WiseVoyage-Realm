# 听景点 Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 17 个真实景点完整录音、持久化、独立播放。
**Architecture:** 独立音频记录表、后端只读播放接口、管理员本地批量录制工具、HTML Audio 播放器。
**Tech Stack:** FastAPI / SQLModel / Vue / 星云 SDK / Chromium MediaRecorder。
**Spec:** docs/superpowers/specs/2026-11-16-scenic-narration-design.md

## Global Constraints
不做假数据、不做假功能；不将密钥或会话 URL 输出到报告；使用星云实际声音。

## Review Focus
空字段不编造；资料变化拒绝旧音频；文件丢失返回未生成；切换和关闭时异步请求不重启播放；录制失败清理星云会话。

## Tasks
- [x] 测试完整讲稿、内容版本和音频缺失行为，再实现 `server/base/modules/scenic_narration.py`、记录表及 `/tour-experience/scenic-audio/{spot_id}`。
- [x] 实现 `scripts/record_scenic_narration.py` 和 `.cjs`，只在本机启动受随机令牌保护的录制桥；逐个朗读并保存星云实际音轨。
- [x] 替换 ScenicDetailView.vue 浏览器朗读与模拟时钟，接入真实 Audio 事件、加载失败和生命周期处理。
- [x] 运行 unittest、前端构建，执行真实数据库批量录制并核对文件数量与时长。

## Execution record
直接在当前目录执行（目录不含 .git，无法创建 worktree 或提交）；用户已确认方案，继续完成授权工作。

2026-11-16：4 项 unittest 通过；vue-tsc 与 Vite 生产构建通过。npm run build 的现有 typography 检查因多个旧文件小字号失败，未改动无关排版。独立复查发现录音捕获开关和开头静音问题，已改为 SDK 的 onAudioPlaybackData 实际 Opus 数据回调，并解码验证时长与非静音。实际试录被自动审批拒绝，原因是需要用户明确同意将景点文本发送至星云；尚未进行云端录制，生成音频数为 0。

用户随后明确授权将17个景点文本发送至已配置星云。真实试录已成功：仁寿殿192.5秒，长廊185.0秒；语音连接需等待后显式进入interactiveidle。SDK通过onAudioPlaybackData返回多个独立Opus段，分别解码并按顺序拼成WAV；时长来自解码样本数。

2026-11-16 16:34 完成全部 17 个景点真实星云录音（spot 1–16、18；总时长约 2765 秒，单条 50.2–192.5 秒）。录制期间星云网关出现多次短时 DNS/WebSocket 抖动，批量脚本按 revision 断点续录，最终 17/17 保存成功，数据库 revision 与讲稿/音色一致。

收尾验证：
- `python scripts/verify_scenic_audio.py`：17/17 OK（数据库记录、revision、WAV 头时长与 DB 一致、非静音）。
- `python -m unittest server.tests.test_scenic_narration -v`：4/4 通过。
- `vue-tsc --build --force` 与 `vite build`：通过（构建产物在 frontend/dist）。
- 重启 18000/18082 后经 5173 逐个探测：17 个景点 `/scenic-audio/{id}` 均 200，`/file` 均 200/206 且 `audio/wav`；不存在景点 404；浏览器实点 17 个景点“听景点”均成功出音频。
- 加固：`/file` 增加二次 recording_file 校验（文件缺失/越界返回 409）；录制保存端点解析 WAV 头核对真实时长并拒绝过短音轨；新增只读核对脚本。
- 已知差异：仁寿殿为 48kHz（18.5MB），其余 16kHz（约 5–6MB）；均可正常播放，如需统一可后续转码。
