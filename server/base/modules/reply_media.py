"""Prepare audio/avatar output independently from verified text delivery."""
import os
from pathlib import Path
from loguru import logger
from ...web_configs import API_CONFIG, WEB_CONFIGS


async def prepare_reply_media(guide, session_id, message_id, text, mode, language, background_tasks):
    from .edge_tts_client import synthesize_speech
    audio_url = ''
    if mode != 'xingyun':
        output = str(Path(WEB_CONFIGS.SERVER_FILE_ROOT) / WEB_CONFIGS.TOUR_FILE_DIR / 'tts')
        os.makedirs(output, exist_ok=True)
        try:
            path = await synthesize_speech(text, voice_style=guide.get('voice_style', 'female_wenrou'),
                                           speed=1.0, output_dir=output, language=language)
            if path and os.path.exists(path):
                audio_url = API_CONFIG.REQUEST_FILES_URL + '/' + WEB_CONFIGS.TOUR_FILE_DIR + '/tts/' + os.path.basename(path)
        except Exception as exc:
            logger.warning('Reply speech unavailable: {}', type(exc).__name__)
    job = None
    if mode == 'realistic' and audio_url:
        from .avatar_runtime import enqueue, render_job
        job = await enqueue(guide['guide_id'], session_id, message_id, audio_url, mode)
        if job.get('job_id'): background_tasks.add_task(render_job, job['job_id'])
    return dict(ttsAudioUrl=audio_url, avatarJob=job)
