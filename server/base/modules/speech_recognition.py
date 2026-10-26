"""Transcribe actual uploaded audio through the configured DashScope service."""
import base64
import os
import subprocess
import shutil
import tempfile
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[3]


async def transcribe_audio(content: bytes) -> str:
    if not content or len(content) > 10 * 1024 * 1024:
        raise ValueError('录音为空或超过10MB，请重新录制')
    key = os.getenv('DASHSCOPE_API_KEY', '').strip()
    if not key:
        raise ValueError('语音识别服务尚未配置，请联系管理员')
    import asyncio
    def normalize():
        with tempfile.TemporaryDirectory(prefix='guide-asr-') as directory:
            source = Path(directory) / 'recording'
            target = Path(directory) / 'speech.wav'
            source.write_bytes(content)
            ffmpeg = ROOT / 'weights/digital_human_weights/drivers/ffmpeg.exe'
            ffmpeg = os.getenv('FFMPEG_PATH') or (str(ffmpeg) if ffmpeg.exists() else shutil.which('ffmpeg'))
            if not ffmpeg:
                raise ValueError('语音识别缺少 FFmpeg 音频转换工具，请联系管理员配置')
            result = subprocess.run([str(ffmpeg), '-hide_banner', '-loglevel', 'error',
                '-i', str(source), '-t', '61', '-ac', '1', '-ar', '16000',
                '-y', str(target)], capture_output=True, timeout=30)
            if result.returncode or not target.exists():
                raise ValueError('无法读取录音，请重新录制')
            import wave
            with wave.open(str(target)) as audio:
                duration = audio.getnframes() / audio.getframerate()
            if duration > 60:
                raise ValueError('录音不能超过60秒')
            return target.read_bytes()
    wav = await asyncio.to_thread(normalize)
    base = os.getenv('MOTION_API_BASE', 'https://dashscope.aliyuncs.com/api/v1').rstrip('/')
    if base.endswith('/api/v1'):
        base = base[:-7]
    url = base + '/compatible-mode/v1/chat/completions'
    payload = {'model': 'qwen3-asr-flash', 'messages': [{'role': 'user', 'content': [
        {'type': 'input_audio', 'input_audio': {'data': 'data:audio/wav;base64,' + base64.b64encode(wav).decode()}}
    ]}], 'stream': False, 'asr_options': {'language': 'zh', 'enable_itn': True}}
    async with httpx.AsyncClient(timeout=75, trust_env=False) as client:
        response = await client.post(url, headers={'Authorization': f'Bearer {key}'}, json=payload)
    if response.status_code != 200:
        raise ValueError('语音识别服务暂时不可用，请检查服务额度后重试')
    try:
        text = response.json()['choices'][0]['message']['content'].strip()
    except (KeyError, IndexError, AttributeError):
        raise ValueError('语音识别服务未返回有效文字')
    if not text:
        raise ValueError('没有识别到语音，请靠近麦克风重新录制')
    return text
