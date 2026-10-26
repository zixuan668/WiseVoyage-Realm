"""Speech playback for the mini program using the existing Edge TTS module."""
import asyncio
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from ...web_configs import API_CONFIG, WEB_CONFIGS
from ..modules.edge_tts_client import synthesize_speech
from ..database.init_db import DB_ENGINE
from ..models.tour_models import DigitalGuideInfo
from ..utils import ResultCode, make_return_data
from .users import get_current_user_info

router = APIRouter(prefix='/tts', tags=['tts'])


@router.get('/edge', summary='导览语音播放')
async def mini_program_speech(
    text: str = Query(min_length=1, max_length=2000),
    language: Literal['zh', 'en'] = 'zh',
    user_id: int = Depends(get_current_user_info),
    guide_id: int | None = Query(default=None, gt=0),
):
    if not text.strip():
        raise HTTPException(422, '朗读文本不能为空')
    output_dir = Path(WEB_CONFIGS.SERVER_FILE_ROOT) / WEB_CONFIGS.TOUR_FILE_DIR / 'tts'
    voice_options = {}
    if guide_id is not None:
        with Session(DB_ENGINE) as session:
            guide = session.get(DigitalGuideInfo, guide_id)
            if guide is None:
                raise HTTPException(404, '数字导游不存在')
            voice_options['voice_style'] = guide.voice_style
    try:
        audio_path = await asyncio.wait_for(
            synthesize_speech(text, output_dir=str(output_dir), language=language, **voice_options), timeout=15,
        )
    except asyncio.TimeoutError:
        raise HTTPException(503, '语音合成超时，请稍后重试')
    if not audio_path or not Path(audio_path).is_file():
        raise HTTPException(503, '语音服务暂不可用，请稍后重试')
    audio_url = API_CONFIG.REQUEST_FILES_URL + '/' + WEB_CONFIGS.TOUR_FILE_DIR + '/tts/' + Path(audio_path).name
    return make_return_data(True, ResultCode.SUCCESS, '语音合成成功', audio_url)
