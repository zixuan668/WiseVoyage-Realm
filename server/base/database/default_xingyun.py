"""从本地配置一次性创建星云导游，后续交由管理端维护。"""
import os

from loguru import logger
from sqlmodel import Session, select

from .init_db import DB_ENGINE
from ..models.tour_models import DigitalGuideInfo
from ..models.user_model import UserInfo
from ..models.xingyun import XingyunBootstrapState, XingyunGuideBinding


def apply_env_english_app():
    """仅补齐缺失的英文绑定；已有管理员配置优先。"""
    app_id = os.getenv("XINGYUN_APP_ID_EN", "").strip()
    secret = os.getenv("XINGYUN_APP_SECRET_EN", "").strip()
    if not app_id or not secret:
        return
    with Session(DB_ENGINE) as db:
        state = db.get(XingyunBootstrapState, "default-guide-v1")
        if not state:
            logger.warning("英文星云应用未应用：默认导游尚未初始化")
            return
        binding = db.get(XingyunGuideBinding, state.guide_id)
        if binding is None:
            logger.warning("英文星云应用未应用：默认导游没有应用绑定")
            return
        if binding.app_id_en and binding.secret_encrypted_en:
            return
        from ..modules.xingyun_access import encrypt_secret
        binding.app_id_en = app_id[:200]
        binding.secret_encrypted_en = encrypt_secret(secret[:500])
        binding.voice_label_en = os.getenv("XINGYUN_VOICE_EN", "").strip()[:80]
        db.add(binding)
        db.commit()
        logger.info("已从 .env 写入英文星云应用凭据（guide_id={}）", state.guide_id)


def initialize_default_xingyun():
    apply_env_english_app()
    app_id = os.getenv("XINGYUN_APP_ID", "").strip()
    secret = os.getenv("XINGYUN_APP_SECRET", "").strip()
    if not app_id or not secret:
        if app_id or secret:
            logger.warning("默认星云导游未初始化：请同时配置 App ID 和 App Secret")
        return
    with Session(DB_ENGINE) as db:
        if db.get(XingyunBootstrapState, "default-guide-v1"):
            return
        owner = db.exec(select(UserInfo).where(
            UserInfo.username == os.getenv("ADMIN_USERNAME", "admin"),
            UserInfo.delete == False,
        )).first()
        if owner is None:
            logger.warning("默认星云导游未初始化：管理员账号尚未创建")
            return
        name = os.getenv("XINGYUN_DEFAULT_GUIDE_NAME", "默认星云导游").strip()
        if not name or len(name) > 30 or len(app_id) > 200 or len(secret) > 500:
            raise ValueError("默认星云导游配置长度无效：名称 1–30、App ID 1–200、App Secret 1–500")
        guide = db.exec(select(DigitalGuideInfo).where(DigitalGuideInfo.name == name)).first()
        if guide is not None:
            # 保留已有记录，包括已被管理员软删除的导游。
            db.add(XingyunBootstrapState(key="default-guide-v1", guide_id=guide.guide_id))
            db.commit()
            logger.info("默认星云导游名称已存在，保留管理员配置")
            return
        from ..modules.xingyun_access import encrypt_secret
        guide = DigitalGuideInfo(
            name=name, user_id=owner.user_id, render_mode="xingyun", is_enabled=True,
            character=os.getenv("XINGYUN_DEFAULT_GUIDE_CHARACTER", ""),
            avatar=os.getenv("XINGYUN_DEFAULT_GUIDE_AVATAR", ""),
            poster_image=os.getenv("XINGYUN_DEFAULT_GUIDE_POSTER", ""),
        )
        db.add(guide)
        db.flush()
        db.add(XingyunGuideBinding(
            guide_id=guide.guide_id, app_id=app_id, secret_encrypted=encrypt_secret(secret),
            voice_label=os.getenv("XINGYUN_DEFAULT_GUIDE_VOICE", ""),
        ))
        db.add(XingyunBootstrapState(key="default-guide-v1", guide_id=guide.guide_id))
        db.commit()
        logger.info("默认星云导游已初始化；云端连接仍需实际验证")
