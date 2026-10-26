"""Shared result formatting, language-model client and administrator bootstrap."""
import os
from datetime import datetime
from ipaddress import IPv4Address

import httpx
from loguru import logger
from openai import OpenAI
from passlib.context import CryptContext
from sqlmodel import Session, select

from .database.init_db import DB_ENGINE
from .models.user_model import UserInfo

# 加载 LLM 模型
LLM_MODEL_HANDLER = OpenAI(
    base_url=os.getenv("LLM_API_BASE", "https://api.siliconflow.cn/v1"),
    api_key=os.getenv("LLM_API_KEY", ""),
    http_client=httpx.Client(timeout=20.0, trust_env=False),
)


class ResultCode:
    SUCCESS: int = 0000  # 成功
    FAIL: int = 1000  # 失败


def make_return_data(success_flag: bool, code: ResultCode, message: str, data: dict):
    return {
        "success": success_flag,
        "code": code,
        "message": message,
        "data": data,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def gen_default_data():
    """Create the configured administrator only; scenic data is imported separately."""
    def create_default_user():
        """按环境变量创建首个管理员，避免仓库内置通用口令。"""
        admin_password = os.environ.get("ADMIN_PASSWORD", "")
        if not admin_password:
            logger.warning("ADMIN_PASSWORD 未配置，已跳过初始管理员创建")
            return False

        password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        from .modules.user_number import assign_user_no

        with Session(DB_ENGINE) as session:
            admin_user = UserInfo(
                username=os.environ.get("ADMIN_USERNAME", "admin"),
                ip_address=IPv4Address("127.0.0.1"),
                email=os.environ.get("ADMIN_EMAIL", "admin@example.com"),
                hashed_password=password_context.hash(admin_password),
                avatar="/user/user-avatar.png",
                user_no=assign_user_no(session),
            )
            session.add(admin_user)
            session.commit()
        return True

    def init_user() -> bool:
        """判断是否需要创建默认用户

        Returns:
            bool: 是否执行创建默认用户
        """
        with Session(DB_ENGINE) as session:
            results = session.exec(select(UserInfo).where(UserInfo.user_id == 1)).first()

        if results is None:
            # 如果数据库为空，创建初始用户
            if create_default_user():
                logger.info("created default user info")
                return True

        return False

    init_user()
