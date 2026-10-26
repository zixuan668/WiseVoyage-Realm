# 管理员侧栏交互

本次按用户给出的菜单交互规范和 make-interfaces-feel-better 实施，仅调整管理员侧栏。

- 选中背景使用同一个高亮块，随目标菜单项位置及尺寸变化；快速切换时连续过渡，文字不参与位移动画。
- 使用现有 Element Plus 的就地折叠展开，并启用单组展开。访问编辑页、详情页时，仍高亮所属菜单；当前子菜单收起后，高亮落在父项。
- 中英文换行、侧栏折叠和窗口尺寸变化会重新对齐高亮块；系统启用减少动态效果时关闭高亮过渡。
- 保留原有八个入口、字体、字号、配色和业务操作。没有新增全局搜索、快捷键、顶部面板、底部停靠栏或虚假未读徽标。

实现入口：`frontend/src/components/AslideComponent.vue`、`frontend/src/utils/adminNavigation.ts`。原顶栏及管理员布局文件已恢复到本次修改前内容；没有保留命令面板组件。

验证：130 项前端测试、TypeScript 检查、字号检查和生产构建通过。`node scripts/check-admin-menu-browser.cjs` 检查生产版页面的 10% 速度高亮、快速重选、单组展开、父项回退、折叠/展开、编辑页定位、中英文与窄窗口、减少动态效果，以及服务站不挂载新侧栏。测试只读取业务数据，服务站访问流程模拟以避免启动数字人。

截图和结果：`work_dirs/admin-menu-20261026/`，最终预览为 `admin-sidebar.png`、`admin-route-menu.png`、`admin-sidebar-en.png` 和 `admin-narrow.png`。修改前或已取消方案的历史图片不是最终结果。
