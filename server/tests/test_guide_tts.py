import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx
from fastapi import FastAPI
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[2] / '.env')
from server.base.routers import tts


class GuideSpeechTests(unittest.IsolatedAsyncioTestCase):
    async def request_speech(self, guide, params):
        app = FastAPI()
        app.include_router(tts.router)
        app.dependency_overrides[tts.get_current_user_info] = lambda: 42
        class FakeSession:
            def __init__(self, *_): pass
            def __enter__(self): return self
            def __exit__(self, *_): pass
            def get(self, *_): return guide
        with tempfile.TemporaryDirectory() as directory:
            audio = Path(directory) / 'speech.mp3'
            audio.write_bytes(b'test audio')
            synth = AsyncMock(return_value=str(audio))
            with patch.object(tts, 'Session', FakeSession, create=True), patch.object(tts, 'synthesize_speech', synth):
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
                    response = await client.get('/tts/edge', params=params)
            return response, synth

    async def test_selected_guide_voice_is_preserved(self):
        response, synth = await self.request_speech(SimpleNamespace(voice_style='male_wenhou'), {'text':'Hello', 'guide_id':2})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(synth.call_args.kwargs.get('voice_style'), 'male_wenhou')

    async def test_missing_guide_does_not_silently_change_the_voice(self):
        response, synth = await self.request_speech(None, {'text':'Hello', 'guide_id':999})
        self.assertEqual(response.status_code, 404)
        synth.assert_not_called()

    async def test_existing_speech_requests_remain_supported(self):
        response, synth = await self.request_speech(None, {'text':'Hello'})
        self.assertEqual(response.status_code, 200)
        synth.assert_awaited_once()


if __name__ == '__main__':
    unittest.main()
