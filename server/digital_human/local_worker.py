"""Local MuseTalk worker. Readiness means an actual loaded GPU model."""
import asyncio
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from loguru import logger

ROOT = Path(__file__).resolve().parents[2]
_handler = None
_runtime = None
_error = '模型尚未加载'
_lock = asyncio.Lock()


def initialize():
    from dotenv import load_dotenv
    load_dotenv(ROOT / '.env')
    os.environ.setdefault('TORCH_HOME', str(ROOT / 'weights/torch_cache'))
    sys.path.insert(0, str(ROOT / 'server/digital_human/modules/musetalk/utils'))
    import torch
    if not torch.cuda.is_available():
        raise RuntimeError('未检测到可用的 CUDA PyTorch 环境')
    from ..web_configs import WEB_CONFIGS
    WEB_CONFIGS.ENABLE_DIGITAL_HUMAN = False
    from .modules import realtime_inference as runtime
    directory = str(ROOT / 'weights/digital_human_weights')
    source = os.environ.get('DIGITAL_HUMAN_SOURCE', str(ROOT / 'static/digital_guide/sources/musetalk-official-sun.mp4'))
    if not Path(source).is_file():
        raise FileNotFoundError('真人基础视频不存在')
    runtime.setup_ffmpeg_env(directory)
    handler = runtime.digital_human_preprocess(directory, True, source, str(ROOT / 'work_dirs/digital_human'), 25, 0)
    return runtime, handler


@asynccontextmanager
async def lifespan(app):
    global _handler, _runtime, _error
    try:
        _runtime, _handler = await asyncio.to_thread(initialize)
        _error = ''
    except Exception as exc:
        _error = f'{type(exc).__name__}: {exc}'
        logger.exception('MuseTalk initialization failed')
    yield


app = FastAPI(lifespan=lifespan)


class DigitalHumanItem(BaseModel):
    user_id: str
    request_id: str = Field(pattern=r'^[A-Za-z0-9_-]{1,96}$')
    streamer_id: str = Field(pattern=r'^[A-Za-z0-9_-]{1,96}$')
    tts_path: str
    chunk_id: int = Field(default=0, ge=0, le=10000)


class DigitalHumanPreprocessItem(BaseModel):
    user_id: str
    request_id: str = Field(pattern=r'^[A-Za-z0-9_-]{1,96}$')
    streamer_id: str = Field(pattern=r'^[A-Za-z0-9_-]{1,96}$')
    video_path: str


def shared_file(value):
    path = Path(value).resolve()
    if not path.is_relative_to((ROOT / 'static').resolve()) or not path.is_file():
        raise HTTPException(400, '素材必须是共享 static 目录内的有效文件')
    return str(path)


@app.get('/digital_human/check')
async def check():
    return {'ready': _handler is not None, 'message': '模型已加载' if _handler is not None else _error}


@app.post('/digital_human/preprocess')
async def preprocess(item: DigitalHumanPreprocessItem):
    if _handler is None:
        raise HTTPException(503, 'MuseTalk 模型未就绪')
    video = shared_file(item.video_path)
    async with _lock:
        await asyncio.to_thread(_runtime.gen_digital_human_preprocess, _handler, item.streamer_id, str(ROOT / 'static/digital_human/vid_output'), video)
    return {'user_id': item.user_id, 'request_id': item.request_id}


@app.post('/digital_human/gen')
async def generate(item: DigitalHumanItem):
    if _handler is None:
        raise HTTPException(503, 'MuseTalk 模型未就绪')
    audio = shared_file(item.tts_path)
    suffix = '' if item.chunk_id == 0 else f'-{item.chunk_id:08d}'
    async with _lock:
        output = await asyncio.to_thread(_runtime.gen_digital_human_video, _handler, item.streamer_id, audio, str(ROOT / 'static/digital_human/vid_output'), item.request_id + suffix + '.mp4', _handler.fps)
    if not output or not Path(output).is_file():
        raise HTTPException(503, '推理没有生成视频')
    return {'user_id': item.user_id, 'request_id': item.request_id, 'digital_human_mp4_path': output}
