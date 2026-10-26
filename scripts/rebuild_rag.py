#!/usr/bin/env python
"""重建景区知识库 RAG（两个 doc 一起）"""
import asyncio
from server.base.modules.rag.rag_worker import rebuild_tour_rag_db
asyncio.run(rebuild_tour_rag_db(1))
