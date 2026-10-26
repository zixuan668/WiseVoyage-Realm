import asyncio
import unittest
from unittest.mock import AsyncMock, patch
from server.base.models.tour_models import TourChatItem
from server.base.modules.tour_dialogue import spoken_answer
from server.base.modules.tour_language import retrieval_question, translate_answer, ENGLISH_UNAVAILABLE
from server.base.modules.edge_tts_client import synthesize_speech


class TourLanguageTests(unittest.TestCase):
    def test_old_clients_remain_chinese_and_unknown_language_is_rejected(self):
        self.assertEqual(TourChatItem(sessionId=1).language, 'zh')
        with self.assertRaises(ValueError):
            TourChatItem(sessionId=1, language='unknown')

    def test_english_question_is_translated_only_for_retrieval(self):
        generate=AsyncMock(return_value='长廊有什么历史故事？')
        result=asyncio.run(retrieval_question('What is the history of the Long Corridor?',generate))
        self.assertEqual(result,'长廊有什么历史故事？')
        self.assertEqual(generate.call_args.kwargs['timeout'],10)
        generate.reset_mock()
        self.assertEqual(asyncio.run(retrieval_question('长廊有什么历史故事？',generate)),'长廊有什么历史故事？')
        generate.assert_not_called()

    def test_retrieval_has_alias_fallback_when_translation_is_unavailable(self):
        result=asyncio.run(retrieval_question('Where can I take photos of Kunming Lake?',AsyncMock(side_effect=TimeoutError)))
        self.assertIn('昆明湖',result)
        self.assertIn('拍照',result)

    def test_direct_route_answer_is_translated_without_changing_route(self):
        generate=AsyncMock(return_value='The next stop is Kunming Lake. Allow about 20 minutes.')
        result=asyncio.run(translate_answer('下一站是昆明湖，建议停留20分钟。',generate))
        self.assertIn('Kunming Lake',result)
        self.assertIn('20',result)
        generate.assert_awaited_once()
        generate.reset_mock()
        self.assertEqual(asyncio.run(translate_answer(result,generate)),result)
        generate.assert_not_called()

    def test_english_failure_is_explicit_instead_of_speaking_chinese(self):
        self.assertEqual(asyncio.run(translate_answer('下一站是昆明湖。')),ENGLISH_UNAVAILABLE)
        self.assertEqual(asyncio.run(translate_answer('下一站是昆明湖。',AsyncMock(return_value='还是中文'))),ENGLISH_UNAVAILABLE)

    def test_english_speech_keeps_sentences_and_word_boundaries(self):
        result=spoken_answer('First sentence. Second sentence. Third sentence.',language='en')
        self.assertEqual(result,'First sentence. Second sentence. Third sentence.')
        result=spoken_answer(' '.join(['information']*200),language='en')
        self.assertLessEqual(len(result.split()),240)
        self.assertTrue(result.endswith('information.'))
        self.assertNotIn('。',result)

    def test_english_uses_english_voice_and_chinese_voice_is_preserved(self):
        with patch('edge_tts.Communicate') as communicate, patch('server.base.modules.edge_tts_client.os.getenv',return_value=''):
            communicate.return_value.save=AsyncMock()
            asyncio.run(synthesize_speech('Welcome to the Summer Palace.',voice_style='male_wenhou',language='en'))
            self.assertEqual(communicate.call_args.args[1],'en-US-GuyNeural')
            asyncio.run(synthesize_speech('欢迎来到颐和园。',voice_style='male_wenhou'))
            self.assertEqual(communicate.call_args.args[1],'zh-CN-YunxiNeural')


if __name__=='__main__': unittest.main()
