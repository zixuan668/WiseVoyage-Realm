import asyncio
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from server.base.modules.windows_speech import SCRIPT, synthesize_windows


@unittest.skipUnless(os.name == 'nt', 'Windows speech is only available on Windows')
class WindowsSpeechTests(unittest.TestCase):
    def test_missing_matching_voice_does_not_select_other_gender(self):
        with tempfile.TemporaryDirectory() as folder:
            output = str(Path(folder) / 'voice.mp3')
            result = MagicMock(returncode=0, stdout='{"available":false}')
            with patch('server.base.modules.windows_speech.subprocess.run', return_value=result) as run:
                self.assertEqual(asyncio.run(synthesize_windows('Hello', 'male_wenhou', .8, output, 'en')), '')
                job = json.loads(run.call_args.kwargs['input'])
                self.assertEqual((job['gender'], job['language'], job['rate']), ('male', 'en', '-20%'))
                self.assertIn('VoiceInfo.Gender', SCRIPT)
                self.assertIn('TwoLetterISOLanguageName', SCRIPT)

    def test_user_text_is_json_stdin_and_matching_audio_is_returned(self):
        with tempfile.TemporaryDirectory() as folder:
            output = str(Path(folder) / 'voice.mp3')
            text = '中文 <标签> $(Remove-Item) `hello`'
            def completed(*args, **kwargs):
                job = json.loads(kwargs['input'])
                Path(job['path']).write_bytes(b'RIFF' + b'\0' * 64)
                return MagicMock(returncode=0, stdout='{"available":true}')
            with patch('server.base.modules.windows_speech.subprocess.run', side_effect=completed) as run:
                result = asyncio.run(synthesize_windows(text, 'male_wenhou', .8, output, 'zh'))
                self.assertEqual(result, str(Path(output).with_suffix('.wav')))
                self.assertEqual(json.loads(run.call_args.kwargs['input'])['text'], text)
                self.assertNotIn(text, run.call_args.args[0])
