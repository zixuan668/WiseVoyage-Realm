# 局域网扫码接入 Android App

## 使用流程

1. 电脑运行数据库、后端 `18000` 与前端 `5173`，手机连接同一个 Wi-Fi。
2. 服务站选择路线，点击“把这条路线带到手机”生成二维码。真实路线快照保存在数据库，领取码有效期为 15 分钟。
3. 扫码进入领取页。已安装 App 时，点击“在 App 中领取路线”。微信可能限制唤起，按页面提示使用系统浏览器打开。
4. 未安装时点击下载 APK，安装后重新扫描二维码。领取码可截图保存，也可在领取网页点击“在 App 中输入领取码”。
5. App 接收路线：点“我的”页右上角“扫码”，在 App 内直接扫描电脑网页上的路线二维码（也可从相册选图）。识别成功后**不再停在领取页**：App 静默领取并直接进入导览（只在二维码来自另一台需要切换地址的电脑时，才落到领取页确认切换）。也可以继续用手机系统相机/浏览器扫码，再点“在 App 中领取路线”唤起 App。
6. 正常点击 App 图标保持原来的引导、登录、首页流程。“我的”页右上角的“扫码”只是领取电脑路线的入口，不改变开机流程。
7. 若二维码里的服务电脑地址与 App 当前连接的地址不同，App 会先确认当前连接的服务电脑上是否已有同一张领取码（开发机常用 USB 反向代理，两个地址指向同一后端）；有就直接领取，不再切换地址、重新登录。确实需要换电脑时才提示切换并重新登录。

局域网 HTTP 仅用于演示；只允许 App 扫码切换到私有 IPv4 地址的 `18000` 端口。切换电脑时清除旧登录令牌，不向另一台电脑发送原登录凭据。电脑地址由 `scripts/configure_app.ps1` 在打包前更新；二维码也包含服务电脑地址。网络变化后需重新生成二维码。

## APK

当前 App 包名为 `cn.zhiyou.guide`，Scheme 为 `zhiyouguide://claim`。Scheme 需要真正打包后的 APK；HBuilderX 通用调试基座不能证明唤起已生效。

HBuilderX 登录后，先确认账号已绑定手机号、当前账号是原 APPID 的所有者或项目成员，并配置该账号可用的 Android 云端证书。公共测试证书已不支持新应用打包。然后执行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/configure_app.ps1
& 'D:\HBuilderX\HBuilderX\cli.exe' pack --project "$PWD\app" --platform android --android.packagename cn.zhiyou.guide --android.androidpacktype 3 --safemode true
python scripts/publish_app_release.py '打包生成的实际APK路径'
```

只有 `static/app/zhiyou-guide.apk` 和 `static/app/release.json` 同时存在时，领取页才提供下载。没有安装包时明确显示“安装包正在准备”，不提供假下载。下载接口：`GET /api/v1/service-stations/app-release`。

## 数据与数字人

`resources/summer-palace-content.zip` 是本次真实公开数据快照，包含景点、路线、数字人公开资料、知识文档和引用素材；SHA256 见同目录校验文件。解压后按 `scripts/import_resource_pack.py` 导入。已有同名数字人和文件不会被覆盖。

数字人的 App ID/Secret、JWT 密钥、账号密码均留在本机 `.env` 和数据库，不进入 Git。当前机器的中文与英文绑定保持不变；重启仅补齐缺失英文绑定。新电脑需自行配置应用密钥后上架，不能靠公共资源包携带密钥。

必须保留本机 JWT 密钥，它用于解密当前数字人的绑定。不要用其他环境的 JWT 密钥替换它。

## 接口与验收

- `POST /service-stations/visits/{visit_id}/share`：返回 token、pickup_code、expires_at；需要该服务站接待凭证。
- `POST /service-stations/claim/preview`：预览，不占用领取资格。
- `POST /service-stations/claim/receive-app`：必须登录；领取并将独立行程关联账号。重复领取幂等，其他账号不能抢走已领取行程。
- `POST /service-stations/claim/receive`：保留原网页领取。

服务站与资源导出测试：

```powershell
$env:PYTHONPATH='scripts/tests;.'
python -m unittest scripts.tests.test_service_stations scripts.tests.test_resource_pack_export
```
