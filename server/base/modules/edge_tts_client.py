#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    :   edge_tts_client.py
@Time    :   2026/06/11
@Desc    :   基于 Edge-TTS 的免费语音合成（无需GPU，无需API Key）
            pip install edge-tts
"""

import asyncio
import os
import tempfile
import uuid
from pathlib import Path

from loguru import logger

# 中文语音列表（女声为主）
VOICE_MAP = {
    "female_wenrou": "zh-CN-XiaoxiaoNeural",      # 温柔女声（推荐）
    "female_huopo": "zh-CN-XiaoyiNeural",           # 活泼女声
    "male_wenhou": "zh-CN-YunxiNeural",             # 温厚男声
    "male_hongliang": "zh-CN-YunjianNeural",        # 洪亮男声
}
ENGLISH_VOICE_MAP = {
    "female_wenrou": "en-US-JennyNeural", "female_huopo": "en-US-AriaNeural",
    "male_wenhou": "en-US-GuyNeural", "male_hongliang": "en-US-ChristopherNeural",
}

# 语速映射
SPEED_MAP = {
    0.8: "-20%",
    0.9: "-10%",
    1.0: "+0%",
    1.2: "+20%",
    1.5: "+50%",
}


async def synthesize_speech(
    text: str,
    voice_style: str = "female_wenrou",
    speed: float = 1.0,
    output_dir: str = "",
    language: str = "zh",
) -> str:
    """使用 Edge TTS 合成语音

    Args:
        text: 要合成的文本
        voice_style: 声音风格
        speed: 语速倍率
        output_dir: 输出目录

    Returns:
        str: 生成的 wav 文件路径
    """
    try:
        import edge_tts
    except ImportError:
        logger.error("edge_tts not installed. Run: pip install edge-tts")
        return ""

    if not text:
        return ""

    voices = ENGLISH_VOICE_MAP if language == "en" else VOICE_MAP
    voice = voices.get(voice_style, voices["female_wenrou"])
    rate = f"{round((max(0.8,min(1.5,float(speed)))-1)*100):+d}%"

    # 清理文本（移除 markdown 语法）
    clean_text = text.replace("**", "").replace("*", "").replace("`", "").replace("#", "")

    # 输出文件
    if not output_dir:
        output_dir = tempfile.gettempdir()
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"tts_{uuid.uuid4().hex[:8]}.mp3")

    proxy=os.getenv("EDGE_TTS_PROXY", "").strip() or None
    # A configured speech proxy is local setup, not a global model/network
    # setting. Both attempts are bounded so a voice outage cannot stall Q&A.
    attempts=[proxy,None] if proxy else [None]
    for attempt_proxy in attempts:
        try:
            communicate = edge_tts.Communicate(clean_text,voice,rate=rate,proxy=attempt_proxy,
                                              connect_timeout=5,receive_timeout=10)
            await asyncio.wait_for(communicate.save(output_file),timeout=15)
            logger.info("Edge TTS synthesized (voice={}, rate={})",voice,rate)
            return output_file
        except Exception as exc:
            logger.warning("Edge TTS attempt unavailable: {}",type(exc).__name__)
            Path(output_file).unlink(missing_ok=True)
    from .windows_speech import synthesize_windows
    return await synthesize_windows(clean_text, voice_style, speed, output_file, language)


def synthesize_speech_sync(text: str, voice_style: str = "female_wenrou", speed: float = 1.0) -> str:
    """同步版本，方便在非 async 上下文中调用"""
    return asyncio.run(synthesize_speech(text, voice_style, speed))
