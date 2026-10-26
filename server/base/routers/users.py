#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    :   users.py
@Time    :   2024/08/30
@Project :   https://github.com/PeterH0323/Streamer-Sales
@Author  :   HinGwenWong
@Version :   1.0
@Desc    :   用户登录和 Token 认证接口
"""

from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from loguru import logger
from passlib.context import CryptContext
from pydantic import BaseModel

from ...web_configs import WEB_CONFIGS
from ..database.user_db import get_db_user_info
from ..models.user_model import TokenItem
from ..utils import ResultCode, make_return_data

router = APIRouter(
    prefix="/user",
    tags=["user"],
    responses={404: {"description": "Not found"}},
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/user/login")

# 密码加解密
PWD_CONTEXT = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """密码校验

    Args:
        plain_password (str): 明文密码
        hashed_password (str): 加密后的密码，用于对比

    Returns:
        bool: 校验时候通过
    """
    return PWD_CONTEXT.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """生成哈希密码

    Args:
        password (str): 明文密码

    Returns:
        str: 加密后的哈希密码
    """
    return PWD_CONTEXT.hash(password)


def authenticate_user(username: str, password: str) -> bool:
    """对用户名和密码进行校验

    Args:
        username (str): 用户名
        password (str): 密码

    Returns:
        bool: 是否检验通过
    """

    # 获取用户信息
    user_info = get_db_user_info(username=username, all_info=True)
    if not user_info:
        # 没有找到用户名
        logger.info(f"Cannot find username = {username}")
        return False

    # 校验密码
    if user_info.delete or not verify_password(password, user_info.hashed_password):
        logger.info(f"verify_password fail")
        # 密码校验失败
        return False

    return user_info


def get_current_user_info(token: str = Depends(oauth2_scheme)):
    """在 token 中提取 user id

    Args:
        token (str, optional): token. Defaults to Depends(oauth2_scheme).

    Raises:
        HTTPException: 401 获取失败

    Returns:
        int: 用户 ID
    """
    if not WEB_CONFIGS.TOKEN_JWT_SECURITY_KEY:
        logger.error("TOKEN_JWT_SECURITY_KEY 未配置")
        raise HTTPException(status_code=503, detail="Authentication service is not configured")
    try:
        token_data = jwt.decode(token, WEB_CONFIGS.TOKEN_JWT_SECURITY_KEY, algorithms=WEB_CONFIGS.TOKEN_JWT_ALGORITHM)
        user_id = token_data.get("user_id", None)
    except Exception as e:
        logger.error(e)
        raise HTTPException(status_code=401, detail="Could not validate credentials")

    if not user_id:
        logger.error(f"can not get user_id: {user_id}")
        raise HTTPException(status_code=401, detail="Could not validate credentials")

    # TODO 超时强制重新登录

    logger.info(f"Got user_id: {user_id}")
    return user_id


class EmailRegistration(BaseModel):
    email: str
    nickname: str
    password: str
    code: str


class EmailCodeRequest(BaseModel):
    email: str


@router.post("/email-code", summary="发送邮箱注册验证码")
def request_email_code(data: EmailCodeRequest, request: Request):
    import secrets
    import time
    from sqlalchemy import text
    from sqlmodel import Session, select
    from ..database.init_db import DB_ENGINE
    from ..models.user_model import UserInfo, EmailVerification
    from ..modules.email_registration import normalize_email, code_digest, send_registration_code

    email = normalize_email(data.email)
    now = int(time.time())
    ip = request.client.host if request.client else 'unknown'
    with Session(DB_ENGINE) as session:
        # Serialize requests, including the first insert, across server workers.
        session.exec(text("SELECT pg_advisory_xact_lock(73192841)"))
        if session.exec(select(UserInfo).where((UserInfo.username == email) | (UserInfo.email == email))).first():
            raise HTTPException(409, "该邮箱已注册，请登录")
        previous = session.get(EmailVerification, email)
        if previous and now - previous.sent_at < 60:
            raise HTTPException(429, "请等待60秒后再发送验证码")
        recent = session.exec(select(EmailVerification).where(
            EmailVerification.sender_ip == ip, EmailVerification.sent_at > now - 600
        )).all()
        if len(recent) >= 10:
            raise HTTPException(429, "验证码请求过于频繁，请稍后再试")
        code = f'{secrets.randbelow(1000000):06d}'
        digest = code_digest(email, code)
        send_registration_code(email, code)
        record = previous or EmailVerification(email=email, code_hash=digest,
            expires_at=now+600, sent_at=now, sender_ip=ip)
        record.code_hash=digest; record.expires_at=now+600
        record.sent_at=now; record.sender_ip=ip; record.attempts=0
        session.add(record)
        session.commit()
    return {"success": True, "message": "验证码已发送，有效期10分钟", "retry_after": 60}


@router.post("/register", summary="验证邮箱并注册")
def register_email(data: EmailRegistration):
    import hmac
    import time
    from sqlalchemy.exc import IntegrityError
    from sqlmodel import Session, select
    from ..database.init_db import DB_ENGINE
    from ..models.user_model import UserInfo, EmailVerification
    from ..modules.email_registration import normalize_email, code_digest
    from ..modules.user_number import assign_user_no

    email = normalize_email(data.email)
    nickname = data.nickname.strip()
    if not nickname or len(nickname) > 40 or '@' in nickname:
        raise HTTPException(400, '昵称需为1至40个字符，不能包含 @')
    # bcrypt 最多支持 72 字节，避免静默截断密码。
    if len(data.password) < 8 or len(data.password.encode('utf-8')) > 72:
        raise HTTPException(400, "密码至少 8 位，UTF-8 编码不超过 72 字节")
    if not WEB_CONFIGS.TOKEN_JWT_SECURITY_KEY:
        raise HTTPException(503, "登录服务未配置 JWT 密钥")
    with Session(DB_ENGINE) as session:
        verification = session.exec(select(EmailVerification).where(
            EmailVerification.email == email).with_for_update()).first()
        if not verification or verification.expires_at <= int(time.time()) or verification.attempts >= 5:
            raise HTTPException(400, "验证码已失效，请重新获取")
        if not hmac.compare_digest(verification.code_hash, code_digest(email, data.code)):
            verification.attempts += 1
            session.add(verification)
            session.commit()
            raise HTTPException(400, "验证码错误")
        existing = session.exec(select(UserInfo).where(
            (UserInfo.username == email) | (UserInfo.email == email)
        )).first()
        if existing:
            raise HTTPException(409, "该邮箱已注册，请登录")
        if session.exec(select(UserInfo).where(UserInfo.username == nickname)).first():
            raise HTTPException(409, '该昵称已被使用，请换一个')
        session.add(UserInfo(username=nickname, email=email,
                             hashed_password=get_password_hash(data.password),
                             create_time=datetime.now(timezone.utc), delete=False,
                             user_no=assign_user_no(session)))
        session.delete(verification)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            raise HTTPException(409, "邮箱或昵称已被使用，请登录或更换")
    return {"success": True, "message": "注册成功，请使用昵称和密码登录"}


@router.post("/login", summary="登录接口")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    if not WEB_CONFIGS.TOKEN_JWT_SECURITY_KEY:
        logger.error("TOKEN_JWT_SECURITY_KEY 未配置")
        raise HTTPException(status_code=503, detail="Authentication service is not configured")
    try:
        # 校验用户名和密码
        username = form_data.username.strip()
        if '@' in username:
            username = username.lower()
        user_info = authenticate_user(username, form_data.password)

        if not user_info:
            raise HTTPException(status_code=401, detail="Incorrect username or password", headers={"WWW-Authenticate": "Bearer"})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {type(e).__name__}: {e}")
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")

    # 过期时间
    token_expires = datetime.now(timezone.utc) + timedelta(days=90)  # 登录一次长期有效，避免每次打开都要登录

    # token 生成包含内容，记录 IP 的原因是防止被其他人拿到用户的 token 进行假冒访问
    token_data = {
        "user_id": user_info.user_id,
        "username": user_info.username,
        "exp": int(token_expires.timestamp()),
        "ip": user_info.ip_address,
        "login_time": int(datetime.now(timezone.utc).timestamp()),
    }
    # 生成 token
    token = jwt.encode(token_data, WEB_CONFIGS.TOKEN_JWT_SECURITY_KEY, algorithm=WEB_CONFIGS.TOKEN_JWT_ALGORITHM)

    # 返回
    res_json = TokenItem(access_token=token, token_type="bearer")
    # return make_return_data(True, ResultCode.SUCCESS, "成功", content)
    return res_json


@router.get("/me", summary="获取用户信息")
async def get_streaming_room_api(user_id: int = Depends(get_current_user_info)):
    """获取用户信息"""
    user_info = get_db_user_info(id=user_id, all_info=True)
    if not user_info or user_info.delete:
        raise HTTPException(401, "登录账号不存在或已停用")
    from ..models.user_model import UserBaseInfo
    user_info = UserBaseInfo(**user_info.model_dump())
    return make_return_data(True, ResultCode.SUCCESS, "成功", user_info)


@router.post("/profile", summary="保存用户头像与昵称")
async def save_user_profile(nickname: str = Form(...), avatar: UploadFile = File(...), user_id: int = Depends(get_current_user_info)):
    import uuid
    from pathlib import Path
    from sqlmodel import Session
    from ..database.init_db import DB_ENGINE
    from ..models.user_model import UserInfo

    nickname = nickname.strip()
    if not nickname or len(nickname) > 40:
        raise HTTPException(400, "昵称须为1至40个字符")
    content = await avatar.read(5 * 1024 * 1024 + 1)
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(400, "头像不能超过5MB")
    if content.startswith(b'\x89PNG\r\n\x1a\n'):
        extension = 'png'
    elif content.startswith(b'\xff\xd8\xff'):
        extension = 'jpg'
    else:
        raise HTTPException(400, "头像仅支持PNG或JPEG图片")
    relative = Path('user_avatars') / str(user_id) / (uuid.uuid4().hex + '.' + extension)
    target = Path(WEB_CONFIGS.SERVER_FILE_ROOT) / relative
    with Session(DB_ENGINE) as session:
        user = session.get(UserInfo, user_id)
        if not user or user.delete:
            raise HTTPException(404, "用户不存在")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        try:
            user.username = nickname
            user.avatar = '/api/v1/files/' + relative.as_posix()
            session.add(user)
            session.commit()
        except Exception:
            session.rollback()
            target.unlink(missing_ok=True)
            raise HTTPException(409, "昵称保存失败，请换一个昵称重试")
        return make_return_data(True, ResultCode.SUCCESS, "资料保存成功", {"username": user.username, "avatar": user.avatar})
