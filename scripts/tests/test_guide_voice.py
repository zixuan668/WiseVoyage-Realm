import asyncio
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from server.base.modules.guide_identity import resolve_guide_voice
from server.base.modules.edge_tts_client import synthesize_speech


class GuideVoiceTests(unittest.TestCase):
    def test_configured_fallback_voice_is_kept(self):
        self.assertEqual(resolve_guide_voice('male_wenhou'), 'male_wenhou')
        self.assertEqual(resolve_guide_voice('female_huopo'), 'female_huopo')
        self.assertEqual(resolve_guide_voice(''), 'female_wenrou')

    def test_slow_and_english_tts_use_configured_male_voice(self):
        communicate=MagicMock()
        communicate.return_value.save=AsyncMock()
        with patch.dict(sys.modules,{'edge_tts':MagicMock(Communicate=communicate)}):
            style=resolve_guide_voice('male_wenhou')
            asyncio.run(synthesize_speech('长廊',voice_style=style,speed=.8))
            self.assertEqual(communicate.call_args.args[1],'zh-CN-YunxiNeural')
            self.assertEqual(communicate.call_args.kwargs['rate'],'-20%')
            asyncio.run(synthesize_speech('Long Corridor',voice_style=style,speed=.8,language='en'))
            self.assertEqual(communicate.call_args.args[1],'en-US-GuyNeural')
            self.assertEqual(communicate.call_args.kwargs['rate'],'-20%')
