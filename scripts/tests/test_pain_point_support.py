import asyncio
import hashlib
import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from sqlmodel import Session, SQLModel, create_engine, select
from server.base.models.tour_models import KnowledgeDocument, KnowledgeReview, TourChatItem
from server.base.modules import knowledge_review
from server.base.modules.rag import rag_worker
from server.base.modules.tour_support import unsupported_numbers, child_fallback
from server.base.modules.tour_dialogue import resolve_turn
from server.base.modules.tour_knowledge import load_book
from test_preference_planner import plan, SPOTS


class PainPointSupportTests(unittest.TestCase):
    def test_exit_and_reserve_are_inside_budget_not_added_after_planning(self):
        for budget in (60,90,120,180):
            for end in ('east','north','south'):
                p=plan(['nature','photography'],budget,start_area='east',end_area=end,queue_reserve_minutes=20)
                self.assertLessEqual(p['estimated_time_minutes'],budget)
                self.assertEqual(p['estimated_time_minutes'],sum(p[k] for k in
                    ('visit_time_minutes','walking_time_minutes','rest_time_minutes','exit_time_minutes','queue_reserve_minutes')))
                if p['spot_ids']:
                    from server.base.modules.walking_network import gate_distance
                    last = next(s for s in SPOTS if s['spot_id']==p['spot_ids'][-1])
                    self.assertEqual(p['exit_time_minutes'], math.ceil(gate_distance(last,end,p['pace']=='relaxed')/(55 if p['pace']=='relaxed' else 75)))
                    self.assertEqual(p['queue_reserve_minutes'],20)
                    self.assertIn('不是实时客流',p['planning_note'])

    def test_user_avoidance_changes_selection_and_remains_explicit(self):
        original=plan(['history'],180)
        p=plan(['history'],180,excluded_spot_ids=original['spot_ids'])
        self.assertTrue(set(original['spot_ids']).isdisjoint(p['spot_ids']))
        self.assertEqual(p['excluded_spot_ids'],sorted(original['spot_ids']))
        self.assertIn('不是无障碍路线认证',p['accessibility_status'])

    def test_numeric_guard_rejects_unseen_numbers_without_claiming_semantic_proof(self):
        self.assertEqual(unsupported_numbers('长廊长728米。','资料：728米'),[])
        self.assertEqual(unsupported_numbers('门票888元。','门票以公告为准'),['888.0'])
        self.assertEqual(unsupported_numbers('It is 728 metres long.','长廊728米。'),[])

    def test_child_explanation_does_not_overwrite_specific_question(self):
        spot=dict(spot_id=2,spot_name='长廊',city='北京')
        intro=resolve_turn('介绍长廊',spot)
        self.assertIn('花鸟画',child_fallback(intro,spot,'fallback'))
        facility=resolve_turn('附近厕所在哪',spot)
        self.assertEqual(child_fallback(facility,spot,'位置未核实'),'位置未核实')
        other=dict(spot,city='上海')
        self.assertEqual(child_fallback(resolve_turn('介绍长廊',other),other,'other'),'other')

    def test_invalid_accessibility_options_rejected_at_api_boundary(self):
        for options in ({'explanation_mode':'anything'},{'language':'anything'}):
            with self.assertRaises(ValueError):TourChatItem(sessionId=1,**options)

    def test_hybrid_evidence_is_scoped_versioned_and_reproducible(self):
        r=rag_worker.LightweightTourRetriever([
            ('长廊.md','<!-- spot:长廊;topic:history -->\n长廊全长728米。'),
            ('佛香阁.md','<!-- spot:佛香阁;topic:history -->\n佛香阁高41米。')])
        a=r.search_evidence('长廊全长',spot_name='长廊',topics=['history'])
        self.assertEqual(a,r.search_evidence('长廊全长',spot_name='长廊',topics=['history']))
        self.assertEqual(a[0]['retrieval_method'],'bm25-char-tfidf-rrf')
        self.assertEqual(a[0]['spot'],'长廊')
        self.assertNotIn('41',a[0]['excerpt'])
        updated=rag_worker.LightweightTourRetriever([('长廊.md','<!-- spot:长廊;topic:history -->\n长廊全长728米，沿湖北岸展开。')])
        self.assertNotEqual(a[0]['version'],updated.search_evidence('长廊全长',spot_name='长廊')[0]['version'])
        self.assertEqual(r.search_evidence('zzzzzzz',spot_name='长廊'),[])


class KnowledgeReviewTests(unittest.TestCase):
    def setUp(self):
        self.engine=create_engine('sqlite://')
        SQLModel.metadata.create_all(self.engine)
        # The retriever also reads scenic records; keep that read inside this test database.
        self.db_patch=patch('server.base.database.init_db.DB_ENGINE',self.engine)
        self.db_patch.start()
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.file=self.root/'new.md'
        self.file.write_text('<!-- spot:长廊;topic:history -->\n长廊长728米。',encoding='utf-8')
        self.digest=hashlib.sha256(self.file.read_bytes()).hexdigest()
        with Session(self.engine) as db:
            db.add(KnowledgeDocument(doc_id=1,title='test',file_path='new.md',content_hash=self.digest,status='pending',user_id=1))
            db.commit()
        self.root_patch=patch.object(knowledge_review.WEB_CONFIGS,'SERVER_FILE_ROOT',str(self.root))
        self.root_patch.start()
        self.index_patch=patch.object(rag_worker,'TOUR_RAG_RETRIEVER',None)
        self.index_patch.start()

    def tearDown(self):
        self.index_patch.stop();self.root_patch.stop();self.db_patch.stop();self.engine.dispose();self.tmp.cleanup()

    def review(self,decision='publish',user=1,digest=None):
        return asyncio.run(knowledge_review.review_document(self.engine,1,user,decision,'核对原文来源',digest or self.digest))

    def test_publication_records_review_and_withdrawal_removes_live_index(self):
        result=self.review()
        self.assertEqual(result['status'],'completed')
        self.assertIn('728',rag_worker.TOUR_RAG_RETRIEVER.query('长廊全长',spot_name='长廊')[1])
        self.review('withdraw')
        self.assertIsNone(rag_worker.TOUR_RAG_RETRIEVER)
        with Session(self.engine) as db:
            self.assertEqual(db.get(KnowledgeDocument,1).status,'pending')
            self.assertEqual(len(db.exec(select(KnowledgeReview)).all()),2)

    def test_foreign_owner_and_changed_preview_version_cannot_publish(self):
        for options in ({'user':2},{'digest':'stale'}):
            with self.assertRaises(ValueError):self.review(**options)
        self.file.write_text('changed',encoding='utf-8')
        with self.assertRaises(ValueError):self.review()
        self.assertIsNone(rag_worker.TOUR_RAG_RETRIEVER)

    def test_index_build_failure_preserves_status_and_audit(self):
        with patch.object(rag_worker,'_load_lightweight_tour_retriever',side_effect=RuntimeError('failure')):
            with self.assertRaises(RuntimeError):self.review()
        with Session(self.engine) as db:
            self.assertEqual(db.get(KnowledgeDocument,1).status,'pending')
            self.assertEqual(db.exec(select(KnowledgeReview)).all(),[])


if __name__=='__main__':unittest.main()
