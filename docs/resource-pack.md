# 颐和园内容导入导出

当前公开包：`resources/summer-palace-content.zip`，16景点、3路线、2数字人、24知识文档。来源与静态文件校验均包含于包内 `resources.json`。

导出使用 `python scripts/export_resource_pack.py <不存在的输出目录> --zip <新的zip路径>`；脚本只导出白名单字段与实际引用的公开素材，排除账号、对话、平台绑定密钥和口型任务。

新部署先配置 `.env`，启动一次后端以初始化表和管理员；解压包，执行 `python scripts/import_resource_pack.py resources/summer-palace-content`，再执行 `python scripts/publish_submitted_knowledge.py --user-id 1` 自动收录导入文档并建立索引。若管理员ID不同，应使用实际管理员ID。

导入保留已有同名内容，ID按导入映射重建；不覆盖管理员已有数字人配置。公开导出包的数字人默认下架，新环境需重新保存真实星云平台绑定后启用。完整私人数据库备份仅用于本机恢复，不应公开分发。
