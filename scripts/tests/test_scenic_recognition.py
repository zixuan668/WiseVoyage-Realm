import unittest
from server.base.modules.scenic_recognition import normalize_result, prepare_image
from fastapi import HTTPException


class ScenicRecognitionTests(unittest.TestCase):
    def setUp(self):
        self.catalog = [{'spot_id': 7, 'spot_name': '测试景点', 'city': '测试城市', 'description': '数据库介绍'}]

    def test_model_cannot_invent_spot_or_description(self):
        result = normalize_result({'recognized': True, 'spot_id': 999, 'evidence': '建筑'}, self.catalog)
        self.assertEqual(result['status'], 'unknown')
        result = normalize_result({'recognized': True, 'spot_id': 7, 'evidence': '标牌', 'description': '伪造介绍'}, self.catalog)
        self.assertEqual(result['description'], '数据库介绍')
        self.assertEqual(result['status'], 'candidate')

    def test_uncertain_result_and_missing_evidence_remain_unknown(self):
        for payload in ({'recognized':False,'spot_id':7,'evidence':'树木'}, {'recognized':True,'spot_id':7}):
            self.assertEqual(normalize_result(payload, self.catalog)['status'], 'unknown')

    def test_invalid_photo_is_rejected(self):
        with self.assertRaises(HTTPException):
            prepare_image(b'not an image')
