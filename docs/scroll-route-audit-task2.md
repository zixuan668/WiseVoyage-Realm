# 后台路由切换滚动位置审计（task-2）

日期：2026-10-29 ｜ 审计员：scroll-auditor ｜ 只读审计，未改产品代码

## 1. 根因结论：确认（一处细节需修正）

- 后台所有业务页挂在同一个 `BaseLayout` 下，内容区 `<el-scrollbar>`（`frontend/src/layouts/BaseLayout.vue`）在路由切换时不会重新创建，
  `scrollTop` 被保留。浏览器在内容变短后会把保留值夹紧到新页面的最大滚动值，于是从长页切到较短的
  「游客反馈分析」时停在**新页面底部**。
- **修正点**：`<transition mode="out-in">` 不是必要条件。Vue 在同一个同步 patch 内移除旧节点、插入新节点，
  期间不触发布局（过渡只做 opacity/transform，不改高度），最终布局看到的就是新内容高度 → 同样夹到新 max。
  实测也支持这一点：从「游客反馈分析」后退到更长的 /home 时，scrollTop 被原样保留为 1575（停在页面中部），
  而不是恢复顶部——说明问题本质是「持久滚动容器 + 路由切换不重置」，过渡只影响时机。
- 影响范围比「切到短页面停在底部」更广：任何路由切换都保留上一页滚动位置（长→短=底部，短→长=中部）。

真实浏览器 A/B 证据（见 `docs/` 与 `.playwright-mcp/`）：
- 关掉修复（浏览器层拦截把 `setScrollTop(0)` 换成 `void 0`，不改文件）：/home 滚到底 1575 → 点「游客反馈分析」
  → 容器 scrollTop = **1077 = 新页面 maxScroll**，第一张统计卡视口 top = **-969**（在屏幕上方不可见）；
  从「游览AI分析」滚到底 2120 → 同样落在 1077（底部）。
- 修复生效：同样操作后 scrollTop = **0**，第一张统计卡视口 top = **108**（可见）；后退回 /home 也是 0。
- 同一路由重复点击（不改变 fullPath）：不触发重置，scrollTop=300 被保留（符合预期）。

## 2. 其它滚动容器/页面的同源排查

**需要处理的：** 无其它。后台只有 BaseLayout 内容区这一个「跨路由持久且承载页面」的滚动容器。

**不需要处理，理由：**
- 侧边栏 `el-aside > el-scrollbar`（BaseLayout）：按设计应保留菜单位置；修复的 ref 只指向内容区实例，结构上不受影响。
- `TourSessionDetailView` 的 `.chat-log{max-height:60vh;overflow-y:auto}`：页面级内部滚动，随页面组件重建而重置；
  且没有 detail→detail 的站内导航路径（侧栏只到 /tour-session/overview）。
- 「游客反馈分析」的 `.comments-grid{max-height:440px;overflow-y:auto}`、各页 `el-table max-height`（300~1000）、
  景点列表标签区 `max-height:96px` 等：都是页面内部容器，随组件重建，不跨路由持久。
- 弹窗类 `el-dialog__body overflow:auto`（admin-readability.scss）与 `StationAdminView` 编辑器
  （已手动 `editorBody.scrollTop = 0`）：打开时重建/已处理。
- 公共端 `StationServiceView`（/station/:stationId，**不在 BaseLayout 内**）使用 window 滚动：
  - 页面内任务切换已有显式处理：`window.scrollTo({top:0})`（task==='home'）+ `scrollIntoView`（路线/服务动作）；
  - 站内没有 /station/A → /station/B 的导航（只有「返回后台」→ /home，回后台时布局 100vh + overflow:hidden，
    window 滚动会被夹回 0），不存在同源问题。
- 登录页自有 overflow：独立路由，不共享布局。
- 路由未配置 `scrollBehavior`（全局 grep 无 savedPosition/scrollBehavior），所以浏览器不会自动恢复外层滚动。
- 项目无 `<keep-alive>`，页面组件路由切换即销毁重建。

## 3. 对 Lead 修复的回归评估

当前实现：`contentScrollbar` ref + `watch(() => route.fullPath, () => setScrollTop(0))`（默认 flush: 'pre'）。

- 后退/前进：每次都会回到顶部。修复前后退是保留任意位置（实测 1575 中部），并不存在「正确的历史位置恢复」，
  所以这是行为改善而非回归；如产品希望恢复，可后续按 fullPath 缓存 scrollTop（本次不建议做）。
- query/hash 变化：`fullPath` 包含 query/hash，因此 query 变化也会回顶。目前后台**没有任何页面使用 query/hash**
  （grep 仅 LoginView / StationServiceView 用 query，且都在布局外），当前无风险；若未来列表页把筛选/分页放 query，
  切换筛选会回顶（通常可接受，也可届时改为 watch route.path）。
- 同一路由重复点击：fullPath 不变 → 不重置（实测保留 300），符合用户预期。
- 侧边栏滚动：ref 只绑内容区 el-scrollbar，侧栏完全不受影响。
- 表格/内部滚动：只操作外层容器，el-table / comments-grid / chat-log 内部 scrollTop 不受影响（且页面重建自然重置）。
- 页面过渡：`out-in` 下重置发生在旧组件仍在场时，旧页面会在 140ms 淡出期间先「跳回顶部」再淡出；
  随后新页从顶部入场。属轻微视觉现象，比停在底部好；不建议为此改成 after-enter 重置（那样新页会先露底部再跳）。
- 首次进入/刷新：watch 非 immediate，首次挂载不会误调用；新加载本来就在顶部。
- 类型：`ScrollbarInstance` 确实是 element-plus 根导出类型（已核对 node_modules/element-plus/es/index.d.ts）。
- 独立跑过 Lead 新增测试：`vitest run src/layouts/__tests__/BaseLayout.spec.ts` → 2 passed。

**建议：** 维持当前修复；可考虑在测试里补一条 query 变化的断言来固化语义（可选），并在提交信息里记录
「所有路由切换回顶，包括后退/前进」。若担心旧页淡出时跳顶，可选方案是把 `transition` 改成不带
`mode="out-in"`（让新内容立即挂载、重置先于新页绘制），但这属于产品动效取舍，不必与本次同改。

## 4. 真实浏览器验证说明

- 5173 端口的 Vite dev server 实际服务于 **另一个检出**（`D:/桌面/WiseVoyage-Realm-main`，BaseLayout 无修复，
  且 api/user.ts 缺 `client_type`，admin 登录返回 403），不能用来验证本工作区的修复。
- 因此用本工作区 `frontend/` 起了一个临时 dev server（5174，node `vite` 直接启动，未改任何产品文件），
  后端 18000 + 无头 Edge（CDP 驱动，真实 UI 登录）完成 A/B。
- A/B 方式：用 CDP Fetch 拦截只替换浏览器内的 BaseLayout 模块（`setScrollTop(0)` → `void 0`），
  同一份代码、同一过渡、同一登录态，仅去掉修复来进行「修复前」复现。
- 截图：`.playwright-mcp/before-A.png`（修复前：反馈页停在底部、卡片不可见）、
  `.playwright-mcp/after-A.png`（修复后：从统计卡片开始显示）。
- 数值记录在上文；另附 `.playwright-mcp/audit-cdp2.mjs` 复现脚本（只读运行，可重复）。

## 5. 附注：菜单与路由的出入

当前侧栏「综合看板」= `/home`（HomeView），「游览AI分析」= `/tour-session/overview`；
`/analytics/dashboard`（路由中的「综合分析看板」）**并未出现在侧栏**。用户所说「综合分析看板」大概率是 /home
（或直接输入 URL 进入 /analytics/dashboard）。做手动验收时请用 /home 或 /tour-session/overview 作为长页起点。
