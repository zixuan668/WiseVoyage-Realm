# App 导览页数字人连接失败：源码回退修复与星云积分不足

反馈：“小程序数字人连不上”，随后确认为 App（不是小程序）。真机导览页显示 `Error: 5, 您的积分不足, 请及时充值（错误码：5）`，下方有“重新连接数字人”。

## 真机证据

- Android 设备已连接（`adb reverse tcp:18000` 生效）。导览页日志：
  - `shouldInterceptRequest file:///.../static/sdk/xmov-avatar-2.4.1-compatible.js`
  - `[ERROR][tour-xingyun] Error: 5, 您的积分不足, 请及时充值（错误码：5）`
- 后端访问日志：`GET /api/v1/xingyun/config/1` 200 → `POST /api/v1/xingyun/session/1?tour_id=23&language=zh` 200 → `DELETE ...` 404。说明会话已创建，客户端拿到星云云端错误后主动释放，连接失败发生在星云云端，而不是本地网络或后端代理。
- 星云错误码 5 是该应用所属账号积分不足/欠费，属于账号额度问题，App 代码无法绕过。

## 同时修复：App 源码回退了数字人兼容修复

排查时发现 `components/tour-xingyun.vue` 与 `pages/tour/tour.vue` 退回到了 1.2.8 之前的写法，仓库自带回归测试因此有 4 项失败：

- 渲染层重新用线上 `@latest` SDK（`script.src=value.sdkUrl`），未使用随包 `static/sdk/xmov-avatar-2.4.1-compatible.js`，Android 硬件解码检查会失败。
- 缺少 `hardwareAcceleration:'prefer-hardware'`。
- 画布仍是 `translateX(-10%)`，没有 `:deep([width][height])` 的铺满/等比/居中规则，SDK 写入的像素尺寸和位移会把画面推偏。
- 旧实例 destroy 未串行化，快速重连时两个 SDK 会同时占用画布。
- 导览舞台不是 16:9 宽画幅。

已按仓库测试与 `app/docs/App-1.2.8-数字人居中修复.md` 恢复：

- renderjs 通过 `common/xingyun-sdk.js` 共享加载随包兼容 SDK，构造参数带 `hardwareAcceleration:'prefer-hardware'`。
- destroy 串行化：旧实例释放完成后才创建新实例。
- 画布限定在 `#tour-xingyun-avatar` 内，强制铺满容器、`transform:none`、`object-fit:contain`、`object-position:50% 50%`；容器 `transform:translateX(0)`。
- 导览舞台改为 `aspect-ratio:16/9` 的居中宽画幅，并对不支持 `aspect-ratio` 的旧 WebView 保留 `height:34vh` 兜底。
- 错误提示：星云错误码 5 不再显示原始 `Error: 5, …（错误码：5）`，改为“星云账号积分不足，请充值后重试（错误码：5）”。

## 验证

- `node --test app/tests/xingyun-sdk.test.cjs`：7 项全部通过（此前 4 项失败）。
- 全部非浏览器 App 测试：140 项通过、0 失败。
- `node app/tests/avatar-layout-browser.cjs`（实际打包 SDK 的布局方法 + 合成画布）：320×640、390×844、844×390、768×1024 及三种 SDK 偏移共 12 组通过；舞台 16:9、人物容器居中、画布铺满且 `object-fit:contain`。
- `node --test app/tests/avatar-audio.test.cjs` 9 项通过；`avatar-audio-browser.cjs` 通过。
- 重新编译 `app/unpackage/dist/build/app-plus`：`app-renderjs.js` 含随包 SDK 与 `prefer-hardware`，包内 SDK 与源码哈希一致，`tour.css` 含 16:9 与画布居中规则。
- 真机日志确认 App 已加载随包 SDK，并走到星云云端返回错误码 5。
- `node app/scripts/verify-avatar-release.cjs` 仍在 AI 聊天页隐藏数字人一项失败（`pages/ai-chat/ai-chat.vue` 的 `chat-voice-runtime`），该文件为并行改动、不在本次范围；导览页数字人相关校验项已通过。

## 后续：更换星云账号凭据

运营在根目录 `.env` 填入新的 `XINGYUN_APP_ID`/`XINGYUN_APP_SECRET`（以及英文 `XINGYUN_APP_ID_EN`/`XINGYUN_APP_SECRET_EN`）后，已用一次性脚本把新凭据加密写入默认导游（guide_id=1，次庄雅）的 `xingyunguidebinding`，并校验加解密成功；旧 App ID `c27ace…` 已替换。后端无需重启：运行时每次连接都从数据库读取绑定；`.env` 的这两个值只在首次初始化默认导游时使用。凭据未写入本文档，也未打印到聊天。

## 未完成 / 需要账号侧处理

- 新星云应用所属账号仍需有可用积分/套餐，否则仍会返回错误码 5。请在 App 导览页点“重新连接数字人”验证；若形象与新应用绑定的角色不一致，需在星云平台把该应用的人物设为“次庄雅”。
- 本机没有充值权限，也未消耗付费会话做成功连接验证；充值后仍需真机确认画面、口型与播报。
- 未打包新的 APK/WGT；当前通过 HBuilderX 基座运行，重跑即可加载新资源。
## 追加排查（2026-10-29 00:35）：换成新凭据后仍是错误码 5

反馈“数字人还是连不上”后重新取证，结论仍是星云账号积分不足，不是本地代码、网络或密钥问题：

- 真机导览页当前仍显示“星云账号积分不足，请充值后重试（错误码：5）”。
- 数据库绑定已确认是新的 App ID `20b03c…e85d`（旧 `c27ace…0cc1` 已替换），最近两条 `xingyunsession` 记录的 `app_id` 也是新值，状态均为 failed。
- 用新凭据直接请求星云网关 `https://nebula-agent.xingyun3d.com/user/v1/ttsa/session`，HTTP 200，返回：

  ```json
  {"error_code": 5, "error_reason": "您的积分不足, 请及时充值"}
  ```

- 对照组：把 App ID 换成不存在的值，返回 `{"error_code": 3, "error_reason": "APP_ID失效"}`。说明新 App ID/Secret 的签名和身份有效，错误码 5 确实是该应用所属账号的积分/套餐问题。
- 星云按数字人交互时长扣积分（基础音色 0.5 积分/分钟，Pro 音色 2 积分/分钟）；余额为 0 时云端不会分配会话资源，客户端只能收到错误码 5，本项目代码无法绕过。

需要账号侧完成：登录魔珐星云控制台（拥有 App ID `20b03c…e85d` 的账号）查看积分/套餐，充值或领取可用积分；确认该应用仍绑定人物“次庄雅”。之后在 App 导览页点“重新连接数字人”。

新增本地自检脚本 `scripts/check_xingyun_credentials.py`：`python scripts/check_xingyun_credentials.py 1`，退出码 0 表示会话可分配（会立即释放测试会话），2 表示仍为积分不足，3 表示其他云端错误。
