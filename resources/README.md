# 颐和园交付内容包

唯一交付资源包为 `summer-palace-content.zip`，对应当前数据库：16个颐和园景点、3条路线、2个数字人展示配置、24份知识文档。

包内含公开内容与实际引用的本地素材；不包含账号、登录凭证、游客对话、平台应用密钥或数据库密码。SHA-256见同目录 `.sha256`。

导入空库的步骤见项目根 README。新环境先初始化管理员，再导入并运行知识发布命令；数字人平台绑定由管理员重新配置。已有本机数据无需重复导入。

旧 `local-resources`、`app-lastest-resources`、`scenic-images` 资源包已移出项目，避免过时内容或非颐和园内容被重复导入。

## 新环境部署顺序（让「听讲解」可用）

1. 按项目根目录 README 初始化数据库，并配置 root 目录的 `.env`（数据库连接等）；
2. 解压内容包后执行：

   ```powershell
   python scripts/import_resource_pack.py 解压后的目录
   ```

   会导入 16 个景点、3 条路线、2 个数字人展示配置和 24 份知识文档；
3. 补齐讲解记录（脚本自动读取根目录 `.env`，可重复执行，已存在则更新）：
   ```powershell
   python scripts/seed_scenic_audio.py
   ```
4. 启动后端，任选一个景点点「听讲解」验证；也可以执行 `python scripts/verify_scenic_audio.py` 检查记录与音频文件是否对应。

说明：16 段讲解音频文件随仓库提供；第 3 步只补数据库记录。未绑定星云数字人、或绑定了另一套星云应用时，接口会播放仓库自带音频（返回来源标记 `bundled-recording`）。

