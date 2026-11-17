import unittest
from server.base.modules import tour_dialogue

class NaturalGuideReplyTests(unittest.TestCase):
    def test_removes_source_prefaces_without_changing_facts(self):
        text='官方资料记载，长廊全长728米、273间。舫身由石料雕砌，官方资料记载长约36米。'
        result=tour_dialogue.natural_guide_reply(text)
        self.assertNotIn('官方资料记载',result)
        for fact in ['728米','273间','约36米']:self.assertIn(fact,result)
    def test_keeps_legends_and_uncertainty(self):
        text='相传铜牛有镇水的寓意，不过最近卫生间的位置还不能确定。'
        self.assertEqual(tour_dialogue.natural_guide_reply(text),text)
    def test_source_question_is_answered_without_stripping_its_subject(self):
        text='官方资料记载了修缮过程，但没有这项测量数据。'
        self.assertEqual(tour_dialogue.natural_guide_reply(text),text)
    def test_keeps_english_unchanged(self):
        text='The bridge was built in 1750.'
        self.assertEqual(tour_dialogue.natural_guide_reply(text,'en'),text)
if __name__=='__main__':unittest.main()
