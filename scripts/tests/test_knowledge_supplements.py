import unittest
from pathlib import Path
from server.base.modules.rag.rag_worker import LightweightTourRetriever, build_tour_rag_prompt


class KnowledgeSupplementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[2] / 'static/tour_files/knowledge_base'
        names = ['summer_palace_visit_guide.md', 'summer_palace_service_guide.md', 'summer_palace_interpretation_guide.md']
        cls.retriever = LightweightTourRetriever([(name, (root / name).read_text(encoding='utf-8')) for name in names])

    def test_park_wide_topics_have_scoped_evidence(self):
        for question, topics, required in [
            ('颐和园的山水与建筑有什么关系', ['architecture'], '万寿山'),
            ('夏天游园怎么防晒，冬天结冰怎么办', ['season'], '补水'),
            ('想带孩子做观察，有哪些游览主题', ['highlights'], '亲子研学'),
        ]:
            with self.subTest(question=question):
                prompt, refs = build_tour_rag_prompt(self.retriever, '颐和园', question, topics)
                self.assertIn(required, prompt)
                self.assertTrue(refs)

    def test_service_evidence_keeps_location_permission_conditions(self):
        rows = self.retriever.search_evidence('接近景点时会自动切换吗', '智能导览服务', ['location'])
        self.assertTrue(rows)
        text = '\n'.join(row['excerpt'] for row in rows)
        self.assertIn('位置权限', text)
        self.assertIn('手动切换', text)
        self.assertIn('不能保证自动触发', text)

    def test_scenic_facts_do_not_mix_with_other_scope_or_live_services(self):
        rows = self.retriever.search_evidence('长廊遮阳避雨有什么作用', '长廊', ['architecture'])
        self.assertTrue(rows)
        self.assertTrue(all(row['spot'] == '长廊' for row in rows))
        self.assertNotIn('苏州街', '\n'.join(row['excerpt'] for row in rows))

    def test_route_examples_do_not_promote_a_fixed_time_guarantee(self):
        rows = self.retriever.search_evidence('经典文化线的用时是多少', '经典文化线', ['duration'])
        self.assertTrue(rows)
        text = '\n'.join(row['excerpt'] for row in rows)
        self.assertIn('不应承诺一个固定总时长', text)


if __name__ == '__main__':
    unittest.main()
