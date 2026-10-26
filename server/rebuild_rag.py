#!/usr/bin/env python
"""重建景区知识库 RAG — 两个doc一起"""
import sys, asyncio
sys.path.insert(0, '/workspace/Streamer-Sales')
from server.base.modules.rag.rag_worker import rebuild_tour_rag_db
asyncio.run(rebuild_tour_rag_db(1))
