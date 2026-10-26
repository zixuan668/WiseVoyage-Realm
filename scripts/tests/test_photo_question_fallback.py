"""摄影问题中的“在哪”不能覆盖摄影意图。"""
import unittest
from server.base.modules.tour_dialogue import resolve_turn, local_answer


def answer_for(spot, question):
    return local_answer(resolve_turn(question, spot), spot)[0]


class PhotoIntentTest(unittest.TestCase):
    def test_photo_question_before_location(self):
        spot = {'spot_name': '测试景点', 'location': '位置字段', 'photo_tips': '摄影档案字段'}
        for word in ('拍照', '拍摄', '摄影', '机位', '取景', '出片', '打卡', '照相'):
            with self.subTest(word=word):
                answer = answer_for(spot, f'最佳{word}点在哪？')
                self.assertIn(spot['photo_tips'], answer)
                self.assertNotIn(spot['location'], answer)
                self.assertNotIn('现在我们来到', answer)

    def test_history_and_nature(self):
        spot = {'spot_name': '测试景点', 'history_detail': '历史字段', 'description': '景观字段', 'photo_tips': '摄影字段'}
        for question, expected in [('历史文化有什么？', '历史字段'), ('自然风光有什么？', '景观字段')]:
            answer = answer_for(spot, question)
            self.assertIn(expected, answer)
            self.assertNotIn('摄影字段', answer)


if __name__ == '__main__':
    unittest.main()
