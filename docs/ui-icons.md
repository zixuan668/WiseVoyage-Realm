# 统一功能图标

本项目按 [make-interfaces-feel-better](https://github.com/jakubkrehel/make-interfaces-feel-better) 的图标规范，使用本地 Lucide 矢量子集。原有宋体、正文和按钮文字字号、浅紫色主题、品牌标志与景点插画保持原设置。

## 文件入口

- `shared/ui-icons.json`：72 个实际使用的 24×24 矢量图形、语义别名和上游版本。
- `shared/ui-icons-LICENSE.txt`：上游授权全文。
- `frontend/src/icons/index.ts`：Vue SVG 组件；使用 `currentColor`，无障碍名称按需传入，装饰图标默认隐藏给读屏。
- `frontend/src/style/icons.scss`：图标线宽、对齐、禁用态及侧栏切换反馈。
- `app/static/iconfont/iconfont-inline.css`：保留原来的图标类名入口，内部改为本地 SVG mask，颜色跟随 `currentColor`，不再请求旧图标字体。
- `app/common/icons.css`：移动端图标尺寸、点击范围及状态反馈。

更新共享图标数据后，在项目根目录运行 `node scripts/build-ui-icons.cjs` 生成兼容资源；无需安装整个图标包，也不需要联网运行。

常规图标用轮廓样式，收藏和评分的选中态使用同一图形的填充表现。移动端常用图标按钮提供至少 44px 点击范围，桌面紧凑控件至少 40px。只有侧栏开关使用 150ms 的透明度、缩放和模糊交叉过渡；减少动态效果偏好会关闭过渡。页面标签的选中态同时保留底托和文字标识。

## 验证入口

- `node --test app/tests/*.test.cjs`
- `frontend` 中运行 `node node_modules/vitest/vitest.mjs run`
- `frontend` 中运行 `node node_modules/vue-tsc/bin/vue-tsc.js --build --force`
- `app/scripts/build-app.ps1 -HBuilderX E:\HBuilderX`
- `node scripts/check-icon-polish-browser.cjs` 检查生产版管理端、服务站功能区和图标状态；服务站访问在截图测试中模拟，不启动付费数字人。

截图及校验日志位于 `work_dirs/iphone-test/icon-polish/`。App 截图是编译后的页面在浏览器中的预览，不能替代 iPhone 真机验证。
