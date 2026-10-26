#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    :   server_info.py
@Time    :   2024/09/02
@Project :   https://github.com/PeterH0323/Streamer-Sales
@Author  :   HinGwenWong
@Version :   1.0
@Desc    :   组件信息获取逻辑
"""


import random
import os
from importlib.util import find_spec
import requests
from loguru import logger

from ..web_configs import API_CONFIG, WEB_CONFIGS


def configured_key(name):
    value = os.getenv(name, "").strip()
    return bool(value) and value not in {"local-demo-disabled", "replace-with-your-provider-key"}


class ServerPluginsInfo:

    def __init__(self) -> None:
        # 启动时不检查，避免卡顿
        self.tts_server_enabled = False
        self.digital_human_server_enabled = False
        self.asr_server_enabled = False
        self.llm_enabled = False
        self.rag_enabled = False  # Set ready only after the retriever has loaded.

    def update_info(self):

        # Configuration is reported without making paid cloud requests.
        self.tts_server_enabled = find_spec("edge_tts") is not None
        self.digital_human_server_enabled = self._check_server(API_CONFIG.DIGITAL_HUMAN_CHECK_URL)
        self.asr_server_enabled = configured_key("DASHSCOPE_API_KEY")
        self.llm_enabled = configured_key("LLM_API_KEY")

        from .modules.rag import rag_worker
        self.rag_enabled = bool(WEB_CONFIGS.ENABLE_RAG and rag_worker.TOUR_RAG_RETRIEVER is not None)

        logger.info(
            "\nself check plugins info : \n"
            f"| llm            | {self.llm_enabled} |\n"
            f"| rag            | {self.rag_enabled} |\n"
            f"| tts            | {self.tts_server_enabled} |\n"
            f"| digital hunam  | {self.digital_human_server_enabled} |\n"
            f"| asr            | {self.asr_server_enabled} |\n"
        )

    @staticmethod
    def _check_server(url):

        try:
            res = requests.get(url, timeout=1)  # 1秒超时，不卡启动
        except Exception:
            return False

        try:
            return res.status_code == 200 and res.json().get("ready") is True
        except (ValueError, AttributeError):
            return False

    @staticmethod
    def _make_color_list(color_num):

        color_list = [
            "#FF3838",
            "#FF9D97",
            "#FF701F",
            "#FFB21D",
            "#CFD231",
            "#48F90A",
            "#92CC17",
            "#3DDB86",
            "#1A9334",
            "#00D4BB",
            "#2C99A8",
            "#00C2FF",
            "#344593",
            "#6473FF",
            "#0018EC",
            "#8438FF",
            "#520085",
            "#CB38FF",
            "#FF95C8",
            "#FF37C7",
        ]

        return random.sample(color_list, color_num)

    def get_status(self):
        self.update_info()

        info_list = [
            {
                "plugin_name": "LLM",
                "describe": "已配置的云端大语言模型，理解游客问题并生成导览讲解；实际可用性以请求结果为准",
                "enabled": self.llm_enabled,
            },
            {
                "plugin_name": "RAG",
                "describe": "检索增强生成，基于景区知识库为数字导游提供准确的景区资料支撑",
                "enabled": self.rag_enabled,
            },
            {
                "plugin_name": "TTS",
                "describe": "Edge TTS 语音合成，支持 Windows 本地语音回退；播放以本轮合成结果为准",
                "enabled": self.tts_server_enabled,
            },
            {
                "plugin_name": "数字人",
                "describe": "数字人驱动（MuseTalk），音频驱动虚拟导游口型同步，需要和 TTS 一起开启",
                "enabled": self.digital_human_server_enabled,
            },
            {
                "plugin_name": "ASR",
                "describe": "百炼 qwen3-asr-flash 云端语音识别；实际可用性以本轮识别结果为准",
                "enabled": self.asr_server_enabled,
            },
        ]

        # 生成图标背景色
        color_list = self._make_color_list(len(info_list))
        for idx, color in enumerate(color_list):
            info_list[idx].update({"avatar_color": color})

        return info_list


SERVER_PLUGINS_INFO = ServerPluginsInfo()
