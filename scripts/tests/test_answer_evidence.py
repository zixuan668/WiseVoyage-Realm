import asyncio
import json
import unittest
from unittest.mock import AsyncMock
from server.base.modules.answer_evidence import answer_segments,validate_review,verify_answer,_CACHE


class AnswerEvidenceTests(unittest.TestCase):
    def setUp(self): _CACHE.clear()

    def test_each_answer_segment_requires_an_actual_quote_and_unique_position(self):
        segments=answer_segments('长廊全长728米。可以分段参观。')
        records={'a':'长廊全长728米。可以按体力分段参观。'}
        review={'checks':[{'segment':1,'supported':True,'quotes':[{'evidence_id':'a','quote':'长廊全长728米。'}]},
                          {'segment':2,'supported':True,'quotes':[{'evidence_id':'a','quote':'可以按体力分段参观。'}]}]}
        self.assertTrue(validate_review(review,segments,records))
        self.assertFalse(validate_review({'checks':review['checks'][:1]},segments,records))
        duplicate=json.loads(json.dumps(review));duplicate['checks'][1]['segment']=1
        self.assertFalse(validate_review(duplicate,segments,records))

    def test_fabricated_quote_or_unknown_source_is_rejected_even_when_model_says_supported(self):
        for source,quote in [('a','长廊全长999米。'),('unknown','长廊全长728米。')]:
            review={'checks':[{'segment':1,'supported':True,'quotes':[{'evidence_id':source,'quote':quote}]}]}
            self.assertFalse(validate_review(review,['长廊全长999米。'],{'a':'长廊全长728米。'}))

    def test_semantic_rejection_and_service_failure_are_fail_closed(self):
        rejected=asyncio.run(verify_answer('长廊是外星人修建的。','长廊是园林走廊。',[],
            AsyncMock(return_value='{"checks":[{"segment":1,"supported":false,"quotes":[]}]}')))
        self.assertEqual(rejected['status'],'rejected')
        failed=asyncio.run(verify_answer('长廊介绍。','长廊是园林走廊。',[],AsyncMock(side_effect=TimeoutError())))
        self.assertEqual(failed['status'],'unavailable')

    def test_cached_review_is_invalidated_by_changed_evidence(self):
        model=AsyncMock(return_value='{"checks":[{"segment":1,"supported":true,"quotes":[{"evidence_id":"local","quote":"长廊全长728米。"}]}]}')
        result=asyncio.run(verify_answer('长廊全长728米。','长廊全长728米。',[],model))
        self.assertEqual(result['status'],'model_checked')
        asyncio.run(verify_answer('长廊全长728米。','长廊全长728米。',[],model))
        self.assertEqual(model.await_count,1)
        result=asyncio.run(verify_answer('长廊全长728米。','资料已撤回，数字未核实。',[],model))
        self.assertEqual(model.await_count,2)
        self.assertEqual(result['status'],'rejected')


if __name__=='__main__':unittest.main()
