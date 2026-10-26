#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    :   base_server.py
@Time    :   2026/06/10
@Project :   景区导览AI数字人
@Desc    :   中台服务入口文件
"""

import time
import uuid
import asyncio
from contextlib import suppress

# 自动加载项目根目录 .env 文件（开发环境免去手动 export 环境变量）
from pathlib import Path as _Path
_dotenv_path = _Path(__file__).resolve().parent.parent.parent / ".env"
if _dotenv_path.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(_dotenv_path)
    except ImportError:
        import os as _os
        # python-dotenv 未安装，尝试手动解析 .env
        with open(_dotenv_path, "r", encoding="utf-8") as _f:
            for _line in _f:
                _line = _line.strip()
                if _line and not _line.startswith("#") and "=" in _line:
                    _key, _val = _line.split("=", 1)
                    _os.environ.setdefault(_key.strip(), _val.strip())
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

from ..web_configs import API_CONFIG, WEB_CONFIGS
from .database.init_db import create_db_and_tables
from .routers import (
    users,
    scenic_spots, knowledge_base, tour_routes, tour_chat, feedback_analytics,
    digital_guide, avatar, spot_favorites, xingyun, tts,
)
from .server_info import SERVER_PLUGINS_INFO, configured_key
from .models import station_models
from .utils import ResultCode, gen_default_data, make_return_data

swagger_description = """

## 项目地址

智游知境 · AI 智能导览平台

基于开源多模态大模型的智能景区导览系统，支持语音/文本交互、数字人口型同步、
个性化路线推荐和游客反馈分析。

## 功能点

1. 🏔️ **景区知识库管理** — PDF/Word/TXT 文档上传与智能切片
2. 📚 **RAG 检索增强生成** — 基于景区资料的高精度问答（准确率≥90%）
3. 🎙️ **ASR 语音转文字** — 游客语音输入识别
4. 🔊 **TTS 文字转语音** — 导游语音合成
5. 🦸 **数字人驱动** — 星云云端数字人 + 可选 MuseTalk 视频生成
6. 🗺️ **个性化路线推荐** — 基于游客偏好匹配最佳游览路线
7. 📊 **游客反馈分析** — 情感分析 + 热点话题 + 满意度趋势
8. 🍍 **三端服务** — Web 管理后台、景区服务站和手机 App
9. 🗝️ FastAPI + PostgreSQL + JWT 身份验证，高性能生产可用
10. 🐋 Docker-compose 一键分布式部署

"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    """服务生命周期函数"""
    # 启动
    logger.info("Step 1/3: 创建/检查数据库表结构...")
    create_db_and_tables()
    from .routers.service_stations import initialize_station
    initialize_station()
    from .modules.avatar_runtime import fail_interrupted_jobs
    fail_interrupted_jobs()

    logger.info("Step 2/3: 检查默认数据...")
    gen_default_data()
    from .database.default_xingyun import initialize_default_xingyun
    initialize_default_xingyun()

    logger.info("Step 3/3: 完成，准备就绪")
    if WEB_CONFIGS.ENABLE_RAG:
        from .modules.rag.rag_worker import load_tour_rag_model

        # 本项目只加载景区知识库；索引或模型暂不可用时保留大模型上下文问答。
        try:
            await load_tour_rag_model(user_id=1)
            SERVER_PLUGINS_INFO.rag_enabled = True
        except Exception as exc:
            SERVER_PLUGINS_INFO.rag_enabled = False
            logger.warning(f"景区 RAG 初始化失败，已降级为景点上下文问答: {exc}")

    from .routers.service_stations import prune_expired_loop
    station_cleanup = asyncio.create_task(prune_expired_loop())
    try:
        yield
    finally:
        station_cleanup.cancel()
        with suppress(asyncio.CancelledError): await station_cleanup
        logger.info("Base server stopped.")


app = FastAPI(
    title="智游知境 · AI 智能导览平台",
    description=swagger_description,
    summary="一个能够为游客提供实时智能问答、个性化路线讲解、情感互动的智游知境。",
    version="2.0.0",
    license_info={
        "name": "AGPL-3.0 license",
        "url": "https://github.com/PeterH0323/Streamer-Sales/blob/main/LICENSE",
    },
    root_path=API_CONFIG.API_V1_STR,
    lifespan=lifespan,
)

from fastapi.middleware.cors import CORSMiddleware

# 浏览器端预览（App H5 / 独立前端）从其他端口访问本服务时需要 CORS 放行
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 数字人服务站、管理员端和 App 共用的景区接口
app.include_router(users.router)
# 景区导览新增路由
app.include_router(scenic_spots.router)
app.include_router(knowledge_base.router)
app.include_router(tour_routes.router)
app.include_router(tour_chat.router)
from .routers import tour_adaptive, tour_experience, service_stations
app.include_router(tour_adaptive.router)
app.include_router(tour_experience.router)
app.include_router(service_stations.router)
app.include_router(tts.router)
app.include_router(feedback_analytics.router)
app.include_router(digital_guide.router)
app.include_router(avatar.router)
app.include_router(spot_favorites.router)
app.include_router(xingyun.router)


# 挂载静态文件目录，以便访问上传的文件
WEB_CONFIGS.SERVER_FILE_ROOT = str(Path(WEB_CONFIGS.SERVER_FILE_ROOT).absolute())
Path(WEB_CONFIGS.SERVER_FILE_ROOT).mkdir(parents=True, exist_ok=True)
logger.info(f"上传文件挂载路径: {WEB_CONFIGS.SERVER_FILE_ROOT}")
logger.info(f"上传文件访问 URL: {API_CONFIG.REQUEST_FILES_URL}")
app.mount(
    f"/{API_CONFIG.REQUEST_FILES_URL.split('/')[-1]}",
    StaticFiles(directory=WEB_CONFIGS.SERVER_FILE_ROOT),
    name=API_CONFIG.REQUEST_FILES_URL.split("/")[-1],
)


@app.get("/")
async def hello():
    return {"message": "智游知境 · AI 智能导览平台"}


@app.get("/system/status", summary="系统服务状态")
async def system_status():
    """获取各子服务的运行状态、数据库连接、API配置信息"""
    import os
    from .database.init_db import DB_ENGINE
    from sqlalchemy import text as sa_text

    # 数据库连通性
    db_ok = False
    db_error = ""
    xingyun_configured = False
    try:
        with DB_ENGINE.connect() as conn:
            conn.execute(sa_text("SELECT 1"))
            db_ok = True
            xingyun_configured = bool(conn.execute(sa_text("""
                SELECT EXISTS (
                    SELECT 1 FROM xingyunguidebinding b
                    JOIN digital_guide_info g ON g.guide_id = b.guide_id
                    WHERE g.delete = FALSE AND g.is_enabled = TRUE
                      AND b.app_id <> '' AND b.secret_encrypted <> ''
                )
            """)).scalar())
    except Exception as e:
        db_error = str(e)[:100]

    # 刷新服务状态
    SERVER_PLUGINS_INFO.update_info()

    # LLM 配置信息
    llm_api_base = os.getenv("LLM_API_BASE", "未配置")
    llm_model = os.getenv("LLM_MODEL_NAME", "未配置")
    llm_key_configured = configured_key("LLM_API_KEY")
    llm_status = "configured" if llm_key_configured else "local_fallback"
    asr_cloud_configured = configured_key("DASHSCOPE_API_KEY")
    asr_status = "configured" if asr_cloud_configured else "unavailable"
    asr_engine = "qwen3-asr-flash（阿里云百炼）"

    return {
        "database": {"status": "connected" if db_ok else "error", "error": db_error},
        "llm": {
            "status": llm_status,
            "api_base": llm_api_base.split("//")[-1] if "//" in llm_api_base else llm_api_base,
            "model": llm_model,
            "key_configured": llm_key_configured,
        },
        "tts": {
            "status": "configured" if SERVER_PLUGINS_INFO.tts_server_enabled else "unavailable",
            "engine": "Edge TTS",
        },
        "asr": {
            "status": asr_status,
            "engine": asr_engine,
            "key_configured": asr_cloud_configured,
        },
        "rag": {"status": "available" if SERVER_PLUGINS_INFO.rag_enabled else "unavailable"},
        "digital_human": {
            "status": "available" if SERVER_PLUGINS_INFO.digital_human_server_enabled
                      else "configured" if xingyun_configured else "unavailable",
            "xingyun_configured": xingyun_configured,
            "musetalk_available": SERVER_PLUGINS_INFO.digital_human_server_enabled,
        },
        "python_version": os.sys.version.split()[0],
    }


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    """调 API 入参错误的回调接口

    Args:
        request (_type_): _description_
        exc (_type_): _description_

    Returns:
        _type_: _description_
    """
    # Validation input and headers may contain application secrets or bearer tokens.
    errors = [{"loc": item["loc"], "msg": item["msg"], "type": item["type"]} for item in exc.errors()]
    logger.info("Request validation failed: {} {}", request.url.path, errors)
    return PlainTextResponse(str(errors), status_code=400)


@app.get("/dashboard", tags=["base"], summary="获取主页信息接口")
async def get_dashboard_info():
    """首页展示数据 — 景区导览运营概览"""
    from datetime import datetime, timedelta

    # 默认值
    spot_count = 0
    doc_count = 0
    guide_count = 0
    route_count = 0
    today_sessions = 0
    week_sessions = 0
    today_questions = 0
    avg_satisfaction = 0.0
    session_trend = [0] * 7
    satisfaction_trend = [0] * 7
    new_session_trend = [0] * 7
    active_user_trend = [0] * 7

    try:
        from .database.init_db import DB_ENGINE
        from sqlmodel import Session, select, func
        from .models.tour_models import (
            ScenicSpotInfo, KnowledgeDocument, DigitalGuideInfo,
            TourRoute, TourSessionInfo, TourSessionStatus,
            VisitorInteraction
        )

        with Session(DB_ENGINE) as db:
            # 景点数
            spot_count = db.scalar(select(func.count(ScenicSpotInfo.spot_id)).where(ScenicSpotInfo.delete == False)) or 0
            # 知识文档数
            doc_count = db.scalar(select(func.count(KnowledgeDocument.doc_id))) or 0
            # 数字导游数
            guide_count = db.scalar(select(func.count(DigitalGuideInfo.guide_id)).where(DigitalGuideInfo.delete == False)) or 0
            # 游览路线数
            route_count = db.scalar(select(func.count(TourRoute.route_id)).where(TourRoute.delete == False)) or 0

            # 当前进行中的会话数
            active_sessions = db.scalar(
                select(func.count(TourSessionStatus.status_id)).where(TourSessionStatus.live_status == 1)
            ) or 0

            # 今日服务人次 & 满意度
            today = datetime.now().date()
            today_start = datetime(today.year, today.month, today.day)
            today_statuses = db.exec(
                select(TourSessionStatus).where(TourSessionStatus.start_time >= today_start)
            ).all()
            today_sessions = len(today_statuses)

            # 本周会话数 & 趋势
            week_start = today_start - timedelta(days=today.weekday())
            for i in range(7):
                day_start = week_start + timedelta(days=i)
                day_end = day_start + timedelta(days=1)
                day_count = db.scalar(
                    select(func.count(TourSessionStatus.status_id))
                    .where(TourSessionStatus.start_time >= day_start, TourSessionStatus.start_time < day_end)
                ) or 0
                session_trend[i] = day_count
                new_session_trend[i] = day_count
            week_sessions = sum(session_trend)

            # 今日问答数
            today_questions = db.scalar(
                select(func.count(VisitorInteraction.message_id))
                .where(VisitorInteraction.send_time >= today_start, VisitorInteraction.role == "user")
            ) or 0

            # 总游客交互数
            total_visitor_interactions = db.scalar(
                select(func.count(VisitorInteraction.message_id))
            ) or 0

            # 知识库文档总块数（近似知识覆盖率）
            total_chunks = db.scalar(
                select(func.coalesce(func.sum(KnowledgeDocument.chunk_count), 0))
            ) or 0
            if total_chunks < 0:
                total_chunks = 0

            # 满意度趋势
            from .modules.sentiment_analyzer import get_emotion_trend_analysis
            recent_interactions = db.exec(
                select(VisitorInteraction)
                .where(VisitorInteraction.send_time >= week_start)
                .order_by(VisitorInteraction.send_time)
            ).all()
            trend_result = get_emotion_trend_analysis(recent_interactions)
            avg_satisfaction = round(trend_result.get("overall_score", 0.5) * 100, 1)

            # 7天满意度趋势（逐天）
            for i in range(7):
                day_start = week_start + timedelta(days=i)
                day_end = day_start + timedelta(days=1)
                day_interactions = [it for it in recent_interactions
                                    if it.send_time and day_start <= it.send_time < day_end]
                if day_interactions:
                    scores = [it.sentiment_score or 0.5 for it in day_interactions]
                    satisfaction_trend[i] = round(sum(scores) / len(scores) * 100, 1)
                else:
                    satisfaction_trend[i] = 0
            # 活跃用户趋势
            for i in range(7):
                day_start = week_start + timedelta(days=i)
                day_end = day_start + timedelta(days=1)
                unique_users = db.exec(
                    select(func.count(func.distinct(VisitorInteraction.user_id)))
                    .where(VisitorInteraction.send_time >= day_start, VisitorInteraction.send_time < day_end)
                ).first()
                active_user_trend[i] = unique_users or 0

    except Exception as e:
        logger.warning(f"Dashboard data query failed, using defaults: {e}")

    dashboard_data = {
        "spotCount": spot_count,
        "docCount": doc_count,
        "guideCount": guide_count,
        "routeCount": route_count,
        "todaySessions": today_sessions,
        "weekSessions": week_sessions,
        "todayQuestions": today_questions,
        "avgSatisfaction": avg_satisfaction,
        "activeSessions": active_sessions,
        "totalInteractions": total_visitor_interactions,
        "totalChunks": total_chunks,
        # 折线图 — 本周每日趋势
        "sessionTrend": session_trend,
        "satisfactionTrend": satisfaction_trend,
        "newSessionTrend": new_session_trend,
        "activeUserTrend": active_user_trend,
    }

    return make_return_data(True, ResultCode.SUCCESS, "成功", dashboard_data)


@app.post("/upload/file", tags=["base"], summary="上传文件接口")
async def upload_file_api(file: UploadFile = File(...), user_id: int = Depends(users.get_current_user_info)):

    file_type = file.filename.split(".")[-1]  # eg. png
    logger.info(f"upload file type = {file_type}")

    sub_dir_name_map = {
        "md": WEB_CONFIGS.INSTRUCTIONS_DIR,
        "png": WEB_CONFIGS.IMAGES_DIR,
        "jpg": WEB_CONFIGS.IMAGES_DIR,
        "mp4": WEB_CONFIGS.STREAMER_INFO_FILES_DIR,
        "wav": WEB_CONFIGS.STREAMER_INFO_FILES_DIR,
        "webm": WEB_CONFIGS.ASR_FILE_DIR,
        # 景区导览新增文件类型
        "pdf": WEB_CONFIGS.KNOWLEDGE_BASE_DIR,
        "docx": WEB_CONFIGS.KNOWLEDGE_BASE_DIR,
        "doc": WEB_CONFIGS.KNOWLEDGE_BASE_DIR,
        "txt": WEB_CONFIGS.KNOWLEDGE_BASE_DIR,
    }
    if file_type in ["wav", "mp4"]:
        save_root = WEB_CONFIGS.STREAMER_FILE_DIR
    elif file_type in ["webm"]:
        save_root = ""
    elif file_type in ["pdf", "docx", "doc", "txt"]:
        save_root = WEB_CONFIGS.TOUR_FILE_DIR
    else:
        save_root = WEB_CONFIGS.PRODUCT_FILE_DIR

    upload_time = str(int(time.time())) + "__" + str(uuid.uuid4().hex)

    sub_dir_name = sub_dir_name_map[file_type]
    save_path = Path(WEB_CONFIGS.SERVER_FILE_ROOT).joinpath(save_root, sub_dir_name, upload_time + "." + file_type)
    save_path.parent.mkdir(exist_ok=True, parents=True)
    logger.info(f"save path = {save_path}")

    # 使用流式处理接收文件
    with open(save_path, "wb") as buffer:
        while chunk := await file.read(1024 * 1024 * 5):  # 每次读取 5MB 的数据块
            buffer.write(chunk)

    split_dir_name = Path(WEB_CONFIGS.SERVER_FILE_ROOT).name  # 保存文件夹根目录名字
    file_url = f"{API_CONFIG.REQUEST_FILES_URL}{str(save_path).split(split_dir_name)[-1]}"

    return make_return_data(True, ResultCode.SUCCESS, "成功", file_url)
