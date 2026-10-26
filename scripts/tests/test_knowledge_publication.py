"""Exercise automatic publication and real retrieval against an isolated database."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine, select

from server.web_configs import WEB_CONFIGS
from server.base.database import init_db, knowledge_doc_db
from server.base.models.user_model import UserInfo
from server.base.models.tour_models import KnowledgeDocument, KnowledgeReview
from server.base.modules.rag import rag_worker
from server.base.modules.knowledge_review import publish_submitted_documents
from server.base.routers import knowledge_base


class KnowledgePublicationTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
        SQLModel.metadata.create_all(self.engine)
        self.files = tempfile.TemporaryDirectory()
        self.addCleanup(self.files.cleanup)
        self.addCleanup(self.engine.dispose)
        for target, name, value in [
            (init_db, 'DB_ENGINE', self.engine),
            (knowledge_doc_db, 'DB_ENGINE', self.engine),
            (knowledge_base, 'DB_ENGINE', self.engine),
            (WEB_CONFIGS, 'SERVER_FILE_ROOT', self.files.name),
            (rag_worker, 'TOUR_RAG_RETRIEVER', None),
        ]:
            item = patch.object(target, name, value)
            item.start()
            self.addCleanup(item.stop)
        with Session(self.engine) as db:
            db.add_all([UserInfo(user_id=i, username='test-owner-' + str(i), hashed_password='unused') for i in (1, 2)])
            db.commit()
        self.app = FastAPI()
        self.app.include_router(knowledge_base.router)
        self.app.dependency_overrides[knowledge_base.get_current_user_info] = lambda: 1
        self.client = TestClient(self.app)
        self.addCleanup(self.client.close)

    def upload(self, content=None):
        if content is None:
            content = '# 长廊\n<!-- spot:长廊;topic:history -->\n## 历史\n长廊全长728米。'.encode('utf-8')
        return self.client.post('/knowledge-base/upload', data={'title': '测试资料'}, files={'file': ('test.md', content, 'text/markdown')}).json()

    def test_upload_is_immediately_published_counted_and_searchable(self):
        result = self.upload()
        self.assertTrue(result['success'], result)
        with Session(self.engine) as db:
            doc = db.get(KnowledgeDocument, result['data']['doc_id'])
            self.assertEqual(doc.status, 'completed')
            self.assertGreater(doc.chunk_count, 0)
            audit = db.exec(select(KnowledgeReview).where(KnowledgeReview.doc_id == doc.doc_id)).one()
            self.assertEqual(audit.status, 'completed')
            self.assertIn('自动', audit.note)
        evidence = rag_worker.TOUR_RAG_RETRIEVER.search_evidence('长廊有多长', '长廊', ['history'])
        self.assertTrue(any('728' in item['excerpt'] for item in evidence))

    def test_invalid_body_is_not_reported_as_published_and_preserves_current_index(self):
        previous = object()
        rag_worker.TOUR_RAG_RETRIEVER = previous
        result = self.upload(b'  \n ')
        self.assertFalse(result['success'])
        with Session(self.engine) as db:
            doc = db.exec(select(KnowledgeDocument)).one()
            self.assertEqual(doc.status, 'failed')
        self.assertIs(rag_worker.TOUR_RAG_RETRIEVER, previous)

    def test_index_failure_keeps_old_snapshot_and_reports_retryable_failure(self):
        previous = object()
        rag_worker.TOUR_RAG_RETRIEVER = previous
        with patch.object(rag_worker, '_load_lightweight_tour_retriever', AsyncMock(side_effect=RuntimeError('index unavailable'))):
            result = self.upload()
        self.assertFalse(result['success'])
        self.assertIs(rag_worker.TOUR_RAG_RETRIEVER, previous)
        with Session(self.engine) as db:
            self.assertEqual(db.exec(select(KnowledgeDocument)).one().status, 'failed')
            self.assertEqual(len(db.exec(select(KnowledgeReview)).all()), 0)

    def test_private_owner_upload_does_not_replace_public_index(self):
        public = object()
        rag_worker.TOUR_RAG_RETRIEVER = public
        self.app.dependency_overrides[knowledge_base.get_current_user_info] = lambda: 2
        result = self.upload()
        self.assertTrue(result['success'], result)
        with Session(self.engine) as db:
            doc = db.get(KnowledgeDocument, result['data']['doc_id'])
            self.assertEqual((doc.user_id, doc.status), (2, 'completed'))
            self.assertGreater(doc.chunk_count, 0)
        self.assertIs(rag_worker.TOUR_RAG_RETRIEVER, public)

    def test_reindex_refreshes_actual_chunk_counts(self):
        result = self.upload()
        with Session(self.engine) as db:
            doc = db.get(KnowledgeDocument, result['data']['doc_id'])
            doc.status = 'completed'
            doc.chunk_count = 0
            db.add(doc)
            db.commit()
        result = self.client.post('/knowledge-base/reindex').json()
        self.assertTrue(result['success'], result)
        with Session(self.engine) as db:
            self.assertGreater(db.exec(select(KnowledgeDocument)).one().chunk_count, 0)

    def test_legacy_batch_failure_does_not_partially_publish(self):
        import asyncio
        root = Path(self.files.name)
        (root / 'valid.md').write_text('# 长廊\n长廊全长728米。', encoding='utf-8')
        (root / 'empty.md').write_text('', encoding='utf-8')
        with Session(self.engine) as db:
            docs = [KnowledgeDocument(title=name, file_path=name, user_id=1, status='pending')
                    for name in ['valid.md', 'empty.md']]
            db.add_all(docs)
            db.commit()
            ids = [doc.doc_id for doc in docs]
        with self.assertRaises(ValueError):
            asyncio.run(publish_submitted_documents(self.engine, 1, ids))
        with Session(self.engine) as db:
            self.assertTrue(all(doc.status == 'pending' for doc in db.exec(select(KnowledgeDocument)).all()))
            self.assertEqual(len(db.exec(select(KnowledgeReview)).all()), 0)

    def test_rag_status_requires_a_loaded_index(self):
        from server.base.server_info import ServerPluginsInfo
        info = ServerPluginsInfo()
        with patch.object(WEB_CONFIGS, 'ENABLE_RAG', True), patch.object(info, '_check_server', return_value=False):
            rag_worker.TOUR_RAG_RETRIEVER = None
            info.update_info()
            self.assertFalse(info.rag_enabled)
            rag_worker.TOUR_RAG_RETRIEVER = object()
            info.update_info()
            self.assertTrue(info.rag_enabled)


if __name__ == '__main__':
    unittest.main()
