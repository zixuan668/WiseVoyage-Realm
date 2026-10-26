import unittest
from server.base.modules.rag.rag_worker import LightweightTourRetriever, build_tour_rag_prompt


class TourRetrievalTests(unittest.TestCase):
    def setUp(self):
        self.retriever=LightweightTourRetriever([
            ('长廊.md','<!-- spot:长廊;topic:history -->\n## 历史\n长廊728米。\n'
             '<!-- spot:长廊;topic:photography -->\n## 摄影\n人物照利用柱列透视，湖景用廊柱作画框。'),
            ('佛香阁.md','<!-- spot:佛香阁;topic:history -->\n## 历史\n佛香阁41米，三层四重檐。\n'
             '<!-- spot:佛香阁;topic:photography -->\n## 摄影\n湖岸拍山体全景，登高注意台阶。'),
            ('旧混合.md','## 长廊\n长廊是彩画廊道。\n## 佛香阁\n佛香阁是高阁。'),
        ])

    def test_entity_filter_rejects_other_sites_even_when_question_mentions_them(self):
        _,context,refs=self.retriever.query('长廊与佛香阁摄影',spot_name='长廊',topics=['photography'])
        self.assertIn('柱列',context)
        self.assertNotIn('41米',context)
        self.assertNotIn('台阶',context)
        self.assertEqual(refs,['长廊.md'])

    def test_topic_filter_does_not_fill_photo_context_with_history(self):
        _,context,_=self.retriever.query('长廊摄影728米',spot_name='长廊',topics=['photography'])
        self.assertIn('画框',context)
        self.assertNotIn('728',context)

    def test_legacy_headings_are_separate_entities(self):
        contexts=[text for (_,text),meta in zip(self.retriever.records,self.retriever.metadata) if meta['spot']=='长廊']
        self.assertTrue(contexts)
        self.assertTrue(all('41米' not in text and '佛香阁是高阁' not in text for text in contexts))

    def test_empty_match_returns_no_arbitrary_top_record(self):
        _,context,refs=self.retriever.query('zzzzzz',spot_name='长廊',topics=['history'])
        self.assertEqual((context,refs),('',[]))
        prompt,refs=build_tour_rag_prompt(self.retriever,'不存在景点','在哪里',['location'])
        self.assertEqual((prompt,refs),('在哪里',[]))

    def test_rag_prompt_preserves_canonical_topic_filters(self):
        prompt, refs = build_tour_rag_prompt(self.retriever, '长廊', '长廊拍照机位有哪些？', ['photography'])
        self.assertIn('柱列', prompt)
        self.assertNotIn('728', prompt)
        self.assertEqual(refs, ['长廊.md'])

    def test_rag_prompt_without_explicit_topics_can_retrieve_history(self):
        prompt, refs = build_tour_rag_prompt(self.retriever, '长廊', '长廊有什么历史？')
        self.assertIn('728', prompt)
        self.assertNotIn('41米', prompt)
        self.assertIn('长廊.md', refs)


if __name__=='__main__': unittest.main()
