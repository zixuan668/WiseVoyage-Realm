#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    :   user_model.py
@Time    :   2024/08/31
@Project :   https://github.com/PeterH0323/Streamer-Sales
@Author  :   HinGwenWong
@Version :   1.0
@Desc    :   用户信息数据结构
"""

from datetime import datetime
from ipaddress import IPv4Address
from pydantic import BaseModel
from sqlmodel import Field, SQLModel


# =======================================================
#                      基本模型
# =======================================================
class TokenItem(BaseModel):
    access_token: str
    token_type: str


class UserBaseInfo(BaseModel):
    user_id: int | None = Field(default=None, primary_key=True, unique=True)
    # 对外展示的用户编号：年月 + 4 位注册顺序，如 2026100001；内部主键仍用 user_id。
    user_no: str | None = Field(default=None, unique=True)
    username: str = Field(index=True, unique=True)
    email: str | None = None
    avatar: str | None = None
    create_time: datetime = datetime.now()


# =======================================================
#                      数据库模型
# =======================================================
class UserInfo(UserBaseInfo, SQLModel, table=True):

    __tablename__ = "user_info"

    hashed_password: str
    ip_address: IPv4Address | None = None
    delete: bool = False
    openid: str | None = None


class EmailVerification(SQLModel, table=True):
    __tablename__ = "email_verification"
    email: str = Field(primary_key=True)
    code_hash: str
    expires_at: int
    sent_at: int
    sender_ip: str = Field(index=True)
    attempts: int = 0


class ScenicRecognition(SQLModel, table=True):
    __tablename__ = "scenic_recognition"
    recognition_id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    result_json: str
    created_at: datetime = Field(default_factory=datetime.now)
