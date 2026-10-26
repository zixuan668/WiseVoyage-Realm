"""Access checks shared by every endpoint exposing a private tour session."""
import os

from fastapi import Header, HTTPException
from sqlmodel import Session

from ..database.init_db import DB_ENGINE
from ..models.tour_models import TourSessionInfo
from ..models.user_model import UserInfo
from ..routers.users import get_current_user_info
from .xingyun_access import authorize_tour


def require_session_access(session_id, authorization=None, access_token=None):
    with Session(DB_ENGINE) as db:
        tour = db.get(TourSessionInfo, session_id)
        if not tour or tour.delete:
            raise HTTPException(404, '导览记录不存在')
        if authorization:
            scheme, _, token = authorization.partition(' ')
            if scheme.lower() != 'bearer' or not token:
                raise HTTPException(401, '登录凭证无效')
            user_id = get_current_user_info(token)
            user = db.get(UserInfo, user_id)
            if not user or user.delete:
                raise HTTPException(401, '账号不可用')
            if tour.user_id == user_id or user.username == os.getenv('ADMIN_USERNAME', 'admin'):
                return
        # A scoped capability also supports anonymous tours and phone pickup.
        # It is checked against both the tour ID and its selected guide.
        if access_token:
            authorize_tour(db, session_id, tour.guide_id, access_token, '', allow_ended=True)
            return
        raise HTTPException(403 if authorization else 401, '无权访问该导览')


def require_path_session(sessionId: int, authorization: str | None = Header(default=None),
                         x_tour_access: str | None = Header(default=None)):
    require_session_access(sessionId, authorization, x_tour_access)
