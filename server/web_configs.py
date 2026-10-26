import os
from dataclasses import dataclass


@dataclass
class WebConfigs:
    """
    项目所有的配置
    """

    # ==================================================================
    #                             服务器文件配置
    # ==================================================================
    SERVER_FILE_ROOT = r"./static"

    # 商品文件（保留兼容）
    PRODUCT_FILE_DIR = "product_files"
    INSTRUCTIONS_DIR = "instructions"
    IMAGES_DIR = "images"

    # 景区导览文件
    TOUR_FILE_DIR = "tour_files"
    SPOT_IMAGES_DIR = "spot_images"
    KNOWLEDGE_BASE_DIR = "knowledge_base"  # 知识库文档存放目录
    TOUR_ROUTE_DIR = "tour_routes"

    # 数字人/数字导游文件
    STREAMER_FILE_DIR = "digital_human"
    STREAMER_INFO_FILES_DIR = "streamer_info_files"
    DIGITAL_GUIDE_FILE_DIR = "digital_guide"  # 数字导游专用目录

    # ASR文件
    ASR_FILE_DIR = "asr"

    # ==================================================================
    #                             JWT 配置
    # ==================================================================

    # JWT Token 加密秘钥，生成命令：openssl rand -hex 32
    TOKEN_JWT_SECURITY_KEY = os.environ.get("TOKEN_JWT_SECURITY_KEY", "")
    TOKEN_JWT_ALGORITHM = "HS256"

    # ==================================================================
    #                             数据库配置
    # ==================================================================
    POSTGRES_SERVER = os.environ.get("POSTGRES_SERVER", "127.0.0.1")  # 数据库 IP
    POSTGRES_PORT = int(os.environ.get("POSTGRES_PORT", "5432"))  # 数据库端口号
    POSTGRES_USER = os.environ.get("POSTGRES_USER", "postgres")  # 数据库用户名
    POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "")  # 数据库密码，自行填写
    POSTGRES_DB = os.environ.get("POSTGRES_DB", "streamer_sales_db")  # 数据库名字

    # 景区检索使用轻量 BM25 + 字符 TF-IDF，无需模型权重或向量数据库。
    ENABLE_RAG: bool = os.environ.get("ENABLE_RAG", "true").strip().lower() == "true"
    # Optional MuseTalk worker configuration; the base API does not load its models.
    ENABLE_DIGITAL_HUMAN: bool = True

    # ==================================================================
    #                             数字人 配置
    # ==================================================================

    DIGITAL_HUMAN_GEN_PATH: str = r"./work_dirs/digital_human"
    DIGITAL_HUMAN_MODEL_DIR: str = r"./weights/digital_human_weights/"
    DIGITAL_HUMAN_BBOX_SHIFT: int = 0
    DIGITAL_HUMAN_VIDEO_PATH: str = rf"{SERVER_FILE_ROOT}/{STREAMER_FILE_DIR}/{STREAMER_INFO_FILES_DIR}/lelemiao.mp4"
    DIGITAL_HUMAN_VIDEO_OUTPUT_PATH: str = rf"{SERVER_FILE_ROOT}/{STREAMER_FILE_DIR}/vid_output"

    DIGITAL_HUMAN_FPS: str = 25



@dataclass
class ApiConfig:
    # ==================================================================
    #                               URL 配置
    # ==================================================================
    API_V1_STR: str = "/api/v1"

    USING_DOCKER_COMPOSE: bool = os.environ.get("USING_DOCKER_COMPOSE", "false") == "true"

    # 路由名字和 compose.yaml 服务名对应
    DIGITAL_ROUTER_NAME: str = "digital_human" if USING_DOCKER_COMPOSE else "127.0.0.1"
    BASE_ROUTER_NAME: str = "base" if USING_DOCKER_COMPOSE else "localhost"


    DIGITAL_HUMAN_URL: str = f"http://{DIGITAL_ROUTER_NAME}:8002/digital_human/gen"
    DIGITAL_HUMAN_CHECK_URL: str = f"http://{DIGITAL_ROUTER_NAME}:8002/digital_human/check"
    DIGITAL_HUMAN_PREPROCESS_URL: str = f"http://{DIGITAL_ROUTER_NAME}:8002/digital_human/preprocess"

    BASE_SERVER_URL: str = f"http://{BASE_ROUTER_NAME}:8000{API_V1_STR}"
    # 图片等静态文件需要浏览器能直接访问，优先使用环境变量，否则根据是否 compose 自动适配
    _FILES_BASE = os.environ.get("FILES_URL_BASE")
    if _FILES_BASE:
        REQUEST_FILES_URL = _FILES_BASE + "/files"
    else:
        REQUEST_FILES_URL = f"http://localhost:8000{API_V1_STR}/files"



# 实例化
WEB_CONFIGS = WebConfigs()
API_CONFIG = ApiConfig()
