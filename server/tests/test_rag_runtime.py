"""The delivered runtime always uses the existing lightweight knowledge retriever."""
import asyncio
import os
import unittest
from unittest.mock import AsyncMock, patch

from server.base.modules.rag import rag_worker


class LightweightRuntimeTests(unittest.TestCase):
    def test_obsolete_vector_setting_cannot_select_a_removed_backend(self):
        retriever = object()
        with patch.dict(os.environ, {'TOUR_RAG_BACKEND': 'vector'}), \
             patch.object(rag_worker, 'TOUR_RAG_RETRIEVER', None), \
             patch.object(rag_worker, '_load_lightweight_tour_retriever', new_callable=AsyncMock, return_value=retriever) as load, \
             patch.object(rag_worker, 'sync_knowledge_chunk_counts') as sync:
            asyncio.run(rag_worker.load_tour_rag_model(1))
            load.assert_awaited_once_with(1)
            sync.assert_called_once_with(1, retriever)
            self.assertIs(rag_worker.TOUR_RAG_RETRIEVER, retriever)

    def test_failed_refresh_keeps_the_last_published_retriever(self):
        published = object()
        with patch.object(rag_worker, 'TOUR_RAG_RETRIEVER', published), \
             patch.object(rag_worker, '_load_lightweight_tour_retriever', new_callable=AsyncMock, side_effect=RuntimeError('invalid document')):
            with self.assertRaises(RuntimeError):
                asyncio.run(rag_worker.rebuild_tour_rag_db(1))
            self.assertIs(rag_worker.TOUR_RAG_RETRIEVER, published)
