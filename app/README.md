# 智游知境 App

本目录是 Android / iPhone 共用的 uni-app Vue 3 源码。在 HBuilderX 中导入 `app/`。Web 景区服务站与管理员位于 `frontend/`，共用后端位于 `server/`；App 的浏览器预览只用于开发验证。

## 开发环境

- 使用 HBuilderX 的 Vue 3 编译器、App 真机运行插件和标准基座。编译器随 HBuilderX 提供；记录交付构建时实际使用的 HBuilderX 与编译器插件版本。
- 保留本仓库的 `manifest.json`、`pages.json`、`shared/coordinates.js` 和 `frontend/src/i18n/en.json`，App 会直接依赖它们。只复制 `app/` 不能完整复现构建。
- 启动仓库现有数据库及后端，沿用根目录 `.env`，后端端口为 18000。不要为测试创建空数据库。
- App 依赖版本保存在 `package-lock.json`。HBuilderX 项目使用内置编译器，不通过 `npm run build` 构建；更新依赖时不要直接升级 `@dcloudio/uni-app`。现有依赖锁包含旧包的 Vue 2 peer 声明，若需恢复这份 npm 依赖，使用 `npm ci --legacy-peer-deps`。

## Android 手机

1. 手机开启 USB 调试，连接电脑并允许调试。在 HBuilderX 选择“运行到 Android App 基座”。
2. 当前 Android 开发版默认通过 USB 访问电脑后端。每次 HBuilderX 重跑后，在仓库根目录执行：

   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts/connect_device_backend.ps1 -Adb E:\HBuilderX\plugins\launcher-tools\tools\adbs\adb.exe
   ```

   该脚本恢复 `adb reverse tcp:18000 tcp:18000` 并检查连接；HBuilderX 重跑可能清除转发。
3. 需要改用同一局域网服务站时，可在登录页的“连接服务站”输入电脑的 `http://局域网IP:18000`。该选择会保存在手机上，并优先于开发版默认值。

## iPhone 手机

当前采用已签名的 HBuilderX 标准基座测试。详细安装和签名步骤见 [iPhone 真机测试](../docs/iphone-testing.md)。

1. iPhone 连接电脑，解锁并信任设备；在 HBuilderX 运行到已签名的 iOS App 基座。
2. iPhone 必须通过局域网或个人热点访问电脑，不能使用 Android 的 USB 反向转发。使用电脑当前有效网卡的局域网地址；网络变化后，在仓库根目录执行以下命令并重新编译：

   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts/configure_app.ps1 -ServerAddress http://电脑当前局域网IP:18000
   ```

3. 先用手机 Safari 打开上述地址加 `/api/v1/tour-session/spots` 检查连通性；App 请求本地网络权限时允许。登录页也可保存新的服务地址。

标准基座的原生权限和 URL Scheme 由基座决定；项目 manifest 的完整原生配置需要匹配的自定义基座或正式安装包。登录和页面启动已有真机记录，数字人声音、声画同步以及外部二维码唤起仍应在目标手机上验收。

## 编译与服务地址

在仓库根目录可执行仅编译 App 资源的命令：

```powershell
powershell -ExecutionPolicy Bypass -File app/scripts/build-app.ps1 -HBuilderX E:\HBuilderX
```

构建输出为 `app/unpackage/dist/build/app-plus/`。这些是编译资源；独立 Android 安装包或 iOS 安装包仍需在 HBuilderX 中打包并签名。`manifest.json` 是交付源码的一部分，缺失时脚本会报错，请恢复该文件后再编译。

正式服务已有 HTTPS 地址时，可以注入构建默认值：

```powershell
powershell -ExecutionPolicy Bypass -File app/scripts/build-app.ps1 -HBuilderX E:\HBuilderX -ServerOrigin https://你的服务域名
```

此命令不会部署服务。地址优先级为：手机保存的连接 > `VITE_APP_SERVER_ORIGIN` 构建值 > 开发默认值。开发默认值在 Android USB 模式为 `http://127.0.0.1:18000`，iPhone 和未注入地址的正式资源为 `common/config.js` 中的局域网地址。旧手机如保存过服务地址，需在登录页主动切换后才会使用新服务。

登录页“连接服务站”先通过公开景点接口检查连接，成功后才保存并要求重新登录；失败会保留当前地址和账号。服务地址支持 HTTPS 域名或私网电脑的 HTTP 18000 端口。

## 服务站路线领取

当前路线领取面向同一局域网的景区服务站，扫描站点路线二维码或输入 12 位领取码，登录后选择数字人并开始导览。App 内扫码可用于标准基座测试；`zhiyouguide://claim` 外部唤起需用包含该 Scheme 的安装包验证。

领取流程仍限定私网电脑的 HTTP 18000 端口；仅配置 HTTPS 登录地址不会使公网路线领取自动可用。本次交付保留现有局域网领取方式。

## 资源与验证

数字人由 `components/tour-xingyun.vue` 通过 renderjs 加载随 App 打包的固定 SDK；路线图同时在 App renderjs 与浏览器预览中使用本地 Leaflet。不要移除 `static/sdk/`、`static/vendor/leaflet/`、当前 SVG 图标样式、品牌与引导插画、路线封面和标记图。正文宋体、字号和淡紫色界面沿用现有样式。

在仓库根目录运行无需手机的检查：

```powershell
node --test app/tests/*.test.cjs
node app/scripts/verify-avatar-release.cjs
```

浏览器回归使用锁定的 `playwright-core` 开发依赖。在 `app/` 目录运行以下命令，即可安装测试工具；该包不附带浏览器，脚本默认使用 Windows 已安装的 Chrome（`C:/Program Files/Google/Chrome/Application/chrome.exe`）。

```powershell
npm ci --legacy-peer-deps
```

需要完整页面的浏览器回归时，先用 HBuilderX 为本 App 生成新的 H5 测试资源，再将 `APP_QA_DIST` 指向含 `index.html` 的输出目录。H5 仅用于验证相同 App 源码。以下命令从仓库根目录运行：

```powershell
$env:APP_QA_DIST = 'E:\App测试构建\h5'
$env:APP_QA_OUT = 'E:\App测试结果'
node app/tests/tabs-switch-browser.cjs
node app/tests/claim-guide-browser.cjs
```

这两个脚本使用随源码提供的 `tests/fixtures/public-catalog.json`：公开景点、数字人和路线数据，不依赖历史 `work_dirs` 输入。与环境配置重合的一处公开导游封面路径已换成本地占位图；fixture 不含账号、密钥或领取凭据。旧 AI 模式切换、旧标签栏及旧路线按钮的三份版本审计脚本已归档，保留当前功能的单元与浏览器回归。

`main-update-browser.cjs`、`tour-flow-browser.cjs`、`spot-category-browser.cjs`、`route-touch-browser.cjs` 也支持 `APP_QA_DIST`。其他浏览器脚本直接使用当前源码、SDK 与本地 Leaflet，无需历史截图或编译输出。测试输出目录可重建；`APP_QA_OUT` 由支持该参数的脚本使用，其他脚本会创建各自的默认输出目录。

自动化测试不替代 Android/iPhone 的相机、麦克风、定位、数字人解码与声音验证。`unpackage/` 为可重建的编译及测试输出，不属于交付源码；保留 `tests/` 和浏览器测试用于开发回归。
