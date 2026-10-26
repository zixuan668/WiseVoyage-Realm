# 管理员知识库自动收录

管理员上传文档后，服务端读取正文并构建替换索引，成功后直接返回“已收录”。页面不再要求预览、填写审核说明或再次发布。文件无法解析或索引构建失败时显示失败，并保留原来的可用索引。

上传、删除、全部重建索引共用知识库写锁；新上传文档的自动收录仍记录在原有审核历史中，便于追溯。分块数量来自当前实际检索分块，旧的零值也会在启动和重建时刷新。私人账户的文档不替换管理员 1 的公共游客知识库。

`ENABLE_RAG=true` 开启检索，默认后端为现有的 `lightweight`：BM25 与字符 TF-IDF 排序融合，不需要下载 GPU 模型；这是检索增强流程，不是另行启动 embedding/FAISS 向量服务。主题过滤使用 history、architecture、photography 等规范值，中文检索扩展词只参与问题检索，不再覆盖主题过滤条件。

现有待审核文档的处理脚本：

```powershell
python scripts/publish_submitted_knowledge.py --user-id 1
```

脚本先将文档和审核记录备份到 `work_dirs/knowledge-autopublish-*.json`，只自动收录尚无审核记录的历史 pending 文档，不恢复已删除、已驳回或明确撤回的资料。本次将 20 份历史提交自动收录，合计 21 份已收录知识文档。已经完成收录后重复执行不会重复处理。

验证：

```powershell
python -m unittest scripts.tests.test_knowledge_publication scripts.tests.test_tour_retrieval scripts.tests.test_tour_dialogue scripts.tests.test_answer_evidence
```

测试覆盖自动收录、真实检索、失败时保持旧索引、空正文、账户隔离、真实分块计数、批量事务和运行状态。服务状态只会在 RAG 开关已开、检索器已加载时显示可用。

真实接口验收记录位于 `work_dirs/knowledge-rag-verification.json`，界面截图位于 `work_dirs/web-run/knowledge-auto-indexed.png`。验收只新增一个明确命名为“RAG索引启用验证”的纯文本问答会话，并在结束时关闭该测试会话，不启用数字人或声音。
