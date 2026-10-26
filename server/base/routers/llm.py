#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    :   llm.py
@Time    :   2024/09/02
@Project :   https://github.com/PeterH0323/Streamer-Sales
@Author  :   HinGwenWong
@Version :   1.0
@Desc    :   大模型接口
"""


from typing import Dict, List
import os
from loguru import logger

from ..utils import LLM_MODEL_HANDLER

def combine_history(prompt: list, history_msg: list):
    """生成对话历史 prompt

    Args:
        prompt (_type_): _description_
        history_msg (_type_): _description_. Defaults to None.

    Returns:
        _type_: _description_
    """
    # 角色映射表（支持导游角色）
    role_map = {"streamer": "assistant", "guide": "assistant", "user": "user"}

    # 生成历史对话信息
    for message in history_msg:
        prompt.append({"role": role_map[message["role"]], "content": message["message"]})

    return prompt


async def gen_guide_base_prompt(
    user_id: int,
    guide_id: int = -1,
    spot_id: int = -1,
    guide_info=None,
    spot_info=None,
    visitor_name: str = "",
) -> list:
    """生成景区导游讲解的 prompt

    Args:
        user_id: 用户 ID
        guide_id: 导游 ID
        spot_id: 景点 ID
        guide_info: 导游信息（DigitalGuideInfo），如果为空则根据 guide_id 查表
        spot_info: 景点信息（ScenicSpotInfo），如果为空则根据 spot_id 查表
        visitor_name: 游客昵称

    Returns:
        List[Dict[str,str]]: 生成的 prompt
    """
    from ..database.digital_guide_db import get_db_digital_guides
    from ..database.scenic_spot_db import get_db_scenic_spot_info

    # 导游系统提示词
    visitor_greeting = (
        f"当前服务的游客昵称是「{visitor_name}」。只在首次欢迎或确有必要时自然称呼一次，"
        "普通问答直接回答内容；禁止每条回复或每个段落固定用游客昵称、导游姓名开头。"
        if visitor_name
        else "禁止每条回复或每个段落固定用导游姓名开头。"
    )
    system_str = (
        "你是{guide_name}，一名专业的景区导游。你的说话风格是{character}。"
        "你精通本景区的历史文化、自然地理、建筑特色等各方面知识。"
        f"{visitor_greeting}"
        "请根据景点信息和知识库资料，为游客提供专业、准确、生动、有温度的导览讲解。"
        "表达像陪游客散步聊天的真人导游，亲切、有情绪回应；根据游客的兴趣和心情调整节奏，不用客服套话或百科腔。"
        "你的回答应该准确有据，采用短句和具体观察引导；不得用自己的印象补充未核实的历史细节。"
        "★ 严禁出现【XX】格式的占位符，每个描述都要写具体。关键事实和数据须基于资料，"
        "未在资料中出现的雕刻纹样、典故和设施位置不要编造。"
        "先直接回答游客的问题；介绍、历史和建筑适当分段展开，具体长度遵循本轮讲解策略。"
        "缺少某项资料时说明具体缺少什么，并提供资料中可确认的相关信息，不要笼统拒绝所有问题。"
    )

    # 获取导游信息
    if guide_info is None:
        guides, _ = await get_db_digital_guides(user_id, guide_id=guide_id)
        if guides:
            guide_info = guides[0]
        else:
            # 使用默认导游信息
            guide_info = type("obj", (object,), {
                "name": "景区导游",
                "character": "博学、亲切、热情",
            })()

    character_str = guide_info.character.replace(";", "、")
    system_str = system_str.replace("{guide_name}", guide_info.name).replace("{character}", character_str)

    # 获取景点信息
    if spot_info is None and spot_id > 0:
        spots, _ = await get_db_scenic_spot_info(user_id, spot_id=spot_id)
        if spots:
            spot_info = spots[0]

    # 构建首轮引导语
    if spot_info is not None:
        spot_name = spot_info.spot_name
        spot_category = spot_info.category
        spot_desc = spot_info.description
        spot_tags = spot_info.tags.replace(";", "、")
        spot_location = spot_info.location
        spot_best_season = spot_info.best_season

        category_map = {
            "natural": "自然风光",
            "historical": "历史文化",
            "cultural": "人文景观",
            "modern": "现代建筑",
            "comprehensive": "综合景点",
        }
        category_cn = category_map.get(spot_category, spot_category)

        first_input = (
            f"你现在位于景区的{spot_location}，眼前就是著名的「{spot_name}」。"
            f"这是一处{category_cn}景点，特色标签包括：{spot_tags}。"
            f"最佳游览季节是{spot_best_season}。"
            f"景点简介：{spot_desc}"
            f"\n\n请作为导游，为游客介绍这个景点的历史文化、特色亮点和有趣的典故，"
            f"并邀请游客提问互动。"
        )
    else:
        first_input = (
            "欢迎游客来到景区！请热情地向游客介绍自己，"
            "询问游客的游览偏好（喜欢历史文化还是自然风光），"
            "并根据游客的偏好推荐合适的游览路线。"
        )

    prompt = [
        {"role": "system", "content": system_str},
        {"role": "user", "content": first_input},
    ]
    logger.debug("Guide prompt prepared: {} messages",len(prompt))

    return prompt


async def get_llm_res(prompt, json_mode: bool = False, timeout: float = 45, *, tour_mode: bool = False):
    """获取 LLM 推理返回

    Args:
        prompt (str): _description_

    Returns:
        _type_: _description_
    """
    logger.debug("LLM request: {} messages; prompt text omitted",len(prompt))
    model_name = os.getenv("LLM_MODEL_NAME", "Qwen/Qwen2.5-7B-Instruct")

    import asyncio

    def _request():
        client = LLM_MODEL_HANDLER.with_options(timeout=timeout, max_retries=0)
        owned_client = None
        selected_model = model_name
        if tour_mode and os.getenv('TOUR_LLM_USE_VISION_PROVIDER', '').lower() == 'true':
            from openai import OpenAI
            import httpx
            owned_client = OpenAI(api_key=os.environ['VISION_API_KEY'],
                base_url=os.environ['VISION_API_BASE'], timeout=timeout, max_retries=0,
                http_client=httpx.Client(timeout=timeout, trust_env=False))
            client = owned_client
            selected_model = os.getenv('VISION_MODEL', 'qwen3-vl-plus')
        request_kwargs = dict(
            model=selected_model,
            messages=prompt,
            stream=False,
            temperature=0.1 if json_mode else 0.35,
            # DeepSeek Flash 会把推理过程计入输出预算；预算过小时可能只
            # 返回 reasoning_content 而 content 为空。
            max_tokens=4096,
        )
        if json_mode:
            request_kwargs["response_format"] = {"type": "json_object"}
        try:
            try:
                return client.chat.completions.create(**request_kwargs)
            except Exception:
                if not json_mode:
                    raise
                logger.warning("当前模型不支持 JSON response_format，回退到提示词约束")
                request_kwargs.pop("response_format", None)
                return client.chat.completions.create(**request_kwargs)
        finally:
            if owned_client is not None:
                owned_client.close()

    # OpenAI SDK 是同步客户端，放入工作线程避免阻塞 FastAPI 事件循环。
    response = await asyncio.to_thread(_request)
    res_data = response.choices[0].message.content or ""
    if not res_data.strip():
        raise RuntimeError("模型未返回可展示内容")
    return res_data.strip()
    # logger.info(prompt)
    # model_name = LLM_MODEL_HANDLER.available_models[0]
    #
    # res_data = ""
    # for item in LLM_MODEL_HANDLER.chat_completions_v1(model=model_name, messages=prompt):
    #     print("LLM response item:", item)
    #     print("Type of item:", type(item))
    #     res_data = item["choices"][0]["message"]["content"]
    #
    # return res_data


async def get_tour_llm_res(prompt, json_mode: bool = False, timeout: float = 45):
    """Keep tour generation, query translation and evidence review on the same provider."""
    import asyncio
    # Bound the entire request, including SDK retries and worker scheduling.
    return await asyncio.wait_for(
        get_llm_res(prompt, json_mode=json_mode, timeout=timeout, tour_mode=True),
        timeout=timeout + 1,
    )
