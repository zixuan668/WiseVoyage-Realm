# 在 Windows 上用 iPhone 测试 App

本项目 App 源码位于仓库的 `app/`。交付测试曾通过签名的 HBuilder 标准基座在 iPhone 上启动并进入登录和导览页面。以下路径和网络地址是示例，使用时应替换成实际安装位置和有效网卡地址；资源编译成功不等于生成独立安装的 iOS 包。

## 没有现成苹果开发证书时

可以先用自己的免费 Apple ID 给 HBuilderX 的标准 iOS 测试基座签名，再从 HBuilderX 同步项目代码。免费签名通常有效 7 天，到期需重新签名。这是第三方签名工具配合 DCloud 基座的调试方式，具体安装结果仍需以手机实测为准。

1. iPhone 用数据线连接电脑，解锁并选择“信任此电脑”。电脑与手机使用同一网络，或开启 iPhone 个人热点并用 USB 连接电脑。
2. HBuilderX 打开仓库的 `app/`。在“工具 → 插件安装”中安装 **App 真机运行**，也可通过“运行 → 运行到手机或模拟器 → 运行到 iOS App 基座”的提示安装。
3. 插件安装完成后，在 HBuilderX 安装目录的 `plugins\launcher\base` 查找标准基座 `iPhone_base.ipa`。基座与签名后的 IPA 不包含在源码仓库中。
4. 本机已使用 iLoader 的“Import IPA”导入标准基座并完成签名安装。需要重新签名时，可在签名工具中选择连接的 iPhone 并导入该 IPA。Apple ID 的登录、验证和密码输入由你在本机完成，不需要发到聊天中。
5. 将签名成功的文件命名为 `iPhone_base_signed.ipa`，放回 `E:\HBuilderX\plugins\launcher\base`。安装已签名文件到 iPhone，并按系统提示信任开发者；需要开发者模式时，在“设置 → 隐私与安全 → 开发者模式”开启并按提示重启。如果该入口尚未出现，先完成开发签名应用的安装或设备配对。
6. 回到 HBuilderX，选择“运行到 iOS App 基座”及已连接的 iPhone。同步完成后，在手机上手动打开基座，检查项目页面。

## 连接电脑后端

- iPhone 可以通过 USB 个人热点连接电脑，使用电脑当前有效网卡地址，例如 `http://192.168.1.20:18000`。断开连接的 Wi-Fi 可能仍显示旧地址，应以处于连接状态的网卡为准。切换网络后，在项目根目录重新运行 `scripts/configure_app.ps1` 更新地址，再重新运行 App。
- iPhone 开发模式使用电脑的局域网地址；Android 开发模式继续保留原有 USB 反向转发。
- 先用 iPhone Safari 打开 `http://192.168.1.20:18000/api/v1/tour-session/spots`（替换实际 IP）。能看到数据，才说明手机可以访问电脑后端；这只是连通性检查，不是另一个 App 预览端。
- App 请求本地网络权限时选择允许，测试期间保持电脑后端运行。如果 Safari 也打不开，应先检查同一 Wi-Fi、电脑防火墙和无线网络设备隔离。

## 测试范围

先验证登录、景点、路线、咨询，再检查数字人、麦克风、相机和定位。标准测试基座的原生权限和 URL Scheme 由基座本身决定，项目 manifest 的原生配置需要匹配的自定义基座或正式 iOS 包才能完整生效；外部扫码唤起 `zhiyouguide://` 不应仅凭标准基座就判定可用，可先在 App 内扫码或输入领取码。

本地 manifest 已补充 iOS 的 `zhiyouguide` Scheme 和局域网使用说明，未填写签名证书或密码。App 字号仍保持恢复后的原版大小。

## 本次声音与聊天框修复（2026-10-25）

- 聊天气泡与底部输入区的布局已修复；用户真机反馈排版正常。App 字号和字体保持原设定。
- iPhone 系统视频可以外放，但 SDK 音频无声。切换原生播放后，日志出现 `-5 MediaError`；文件请求成功，服务端 WAV 文件可正常解析。
- 用户明确拒绝整段下载后播放。该流程已撤掉，星云导览不再请求独立 TTS，也不再静音 SDK 音轨。语音、口型与停止操作统一交给原 SDK 会话控制。
- iPhone 的 SDK 实时输出改接 `MediaStreamAudioDestinationNode`，再交给同一渲染窗口中的音频元素播放实时流；没有文件地址、完整下载或第二份配音。Android 保留原输出通道。此改动用于验证 iPhone 输出通道问题，不代表已确认真机恢复。
- “开启声音”在用户手势内同时恢复 SDK 音频时钟和实时媒体输出；若播放被系统拒绝，按钮继续提供重试。页面退出会释放自己创建的流、音频元素和输出拦截，不影响已有的其他音频上下文。
- 浏览器测试使用实际 SDK 的 PCM 处理器和合成测试音，检查实时流有非零采样、播放状态及清理。历史结果和构建日志属于本机归档，不包含在公开源码中。
- 是否恢复可听声音、实际延迟与声画同步仍待目标 iPhone 真机确认，不应视为已经修复。

## 官方参考

- [DCloud：iOS 标准基座签名与第三方签名步骤](https://uniapp.dcloud.net.cn/tutorial/run/ios-apple-certificate-signature.html)
- [爱思助手：Apple ID 免费 IPA 签名](https://helper.i4.cn/news_detail_38195.html)
- [Apple：开启设备开发者模式](https://developer.apple.com/documentation/xcode/enabling-developer-mode-on-a-device)
