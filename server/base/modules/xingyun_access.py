import base64
import hashlib
import os
from datetime import datetime, timedelta, timezone

import jwt
from cryptography.fernet import Fernet, InvalidToken
from fastapi import Depends, HTTPException
from sqlmodel import Session

from ...web_configs import WEB_CONFIGS
from ..database.init_db import DB_ENGINE
from ..models.tour_models import DigitalGuideInfo, TourSessionInfo
from ..models.user_model import UserInfo
from ..models.xingyun import XingyunGuideBinding
from ..routers.users import get_current_user_info


def require_guide_admin(user_id: int = Depends(get_current_user_info)):
    with Session(DB_ENGINE) as db:
        user = db.get(UserInfo, user_id)
        if not user or user.delete or user.username != os.getenv("ADMIN_USERNAME", "admin"):
            raise HTTPException(403, "仅管理员可管理数字导游")
    return user_id


def cipher():
    key = WEB_CONFIGS.TOKEN_JWT_SECURITY_KEY
    if not key:
        raise HTTPException(503, "服务端未配置密钥加密所需的 JWT 密钥")
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(key.encode()).digest()))


def encrypt_secret(value: str):
    return cipher().encrypt(value.encode()).decode()


def decrypt_secret(value: str):
    try:
        return cipher().decrypt(value.encode()).decode()
    except (InvalidToken, ValueError):
        raise HTTPException(503, "星云凭据无法解密，请管理员重新保存应用密钥")


def selectable(db, guide):
    if not guide or guide.delete or not guide.is_enabled:
        return False
    if guide.render_mode != "xingyun":
        return True
    binding = db.get(XingyunGuideBinding, guide.guide_id)
    return bool(binding and binding.app_id and binding.secret_encrypted)


def issue_tour_avatar_token(tour):
    # 匿名游客获得只允许本次导览、所选人物连接星云的短期凭证。
    if not WEB_CONFIGS.TOKEN_JWT_SECURITY_KEY:
        return ""
    return jwt.encode({"purpose": "xingyun-tour", "tour_id": tour.session_id,
                       "guide_id": tour.guide_id,
                       "exp": datetime.now(timezone.utc) + timedelta(hours=24)},
                      WEB_CONFIGS.TOKEN_JWT_SECURITY_KEY, algorithm="HS256")


def authorize_tour(db, tour_id, guide_id, access_token, authorization, allow_ended=False):
    tour = db.get(TourSessionInfo, tour_id)
    if not tour or tour.delete or tour.guide_id != guide_id:
        raise HTTPException(403, "导览与所选数字人不匹配")
    if not allow_ended and tour.status and tour.status.live_status == 2:
        raise HTTPException(409, "导览已结束，请重新选择数字人开始导览")
    if access_token:
        try:
            claims = jwt.decode(access_token, WEB_CONFIGS.TOKEN_JWT_SECURITY_KEY, algorithms=["HS256"])
            if claims.get("purpose") != "xingyun-tour" or claims.get("tour_id") != tour_id or claims.get("guide_id") != guide_id:
                raise ValueError()
        except (jwt.PyJWTError, ValueError):
            raise HTTPException(401, "导览凭证无效或已过期，请重新开始导览")
    elif authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token or tour.user_id != get_current_user_info(token):
            raise HTTPException(403, "无权连接该导览的数字人")
    else:
        raise HTTPException(401, "请从数字人选择页重新开始导览")
    return tour
