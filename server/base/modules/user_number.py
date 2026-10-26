"""对外展示的用户编号：年月 + 4 位注册顺序，例如 2026100001。

内部主键仍是 user_info.user_id（整数），本模块只负责生成持久化到 user_info.user_no 的展示编号：

- 年月按北京时间取，注册当月第 1 位为 0001，下个月重新从 0001 开始；
- 同一事务内用 PostgreSQL 咨询锁串行化取号，避免并发注册拿到重复编号；
- 启动时把历史账号按注册顺序补号，保证老账号也有稳定编号。
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlmodel import Session, select

from ..models.user_model import UserInfo

# 用户编号取号锁，和验证码等其它咨询锁使用不同的 key。
USER_NO_LOCK_KEY = 73192842
USER_NO_SEQ_DIGITS = 4
USER_NO_MAX_SEQ = 10 ** USER_NO_SEQ_DIGITS - 1
USER_NO_TZ = timezone(timedelta(hours=8))


def month_prefix(now: datetime | None = None) -> str:
    """返回编号里的年月前缀，例如 202610。"""
    current = now or datetime.now(USER_NO_TZ)
    if current.tzinfo is not None:
        current = current.astimezone(USER_NO_TZ)
    return current.strftime("%Y%m")


def _lock_user_numbers(session: Session) -> None:
    """同一数据库内串行取号；SQLite（单元测试）没有咨询锁，跳过。"""
    if session.get_bind().dialect.name == "postgresql":
        session.exec(text(f"SELECT pg_advisory_xact_lock({USER_NO_LOCK_KEY})"))


def _format_user_no(prefix: str, sequence: int) -> str:
    if sequence < 1 or sequence > USER_NO_MAX_SEQ:
        raise RuntimeError(f"用户编号序号超出范围: {sequence}")
    return f"{prefix}{sequence:0{USER_NO_SEQ_DIGITS}d}"


def _last_sequence(session: Session, prefix: str) -> int:
    last = session.exec(
        select(UserInfo.user_no)
        .where(UserInfo.user_no.like(f"{prefix}%"))
        .order_by(UserInfo.user_no.desc())
        .limit(1)
    ).first()
    if not last:
        return 0
    return int(last[-USER_NO_SEQ_DIGITS:])


def assign_user_no(session: Session, now: datetime | None = None) -> str:
    """在调用方事务内分配下一个用户编号，例如 2026100002。"""
    _lock_user_numbers(session)
    prefix = month_prefix(now)
    return _format_user_no(prefix, _last_sequence(session, prefix) + 1)


def backfill_user_numbers(engine, now: datetime | None = None) -> int:
    """为缺少 user_no 的历史账号补号，返回补号数量。

    历史账号统一按当前年月、按注册顺序连续编号；已有编号的账号保持不动，
    因此服务重启不会重复编号，也不会打乱已发放的编号。
    """
    prefix = month_prefix(now)
    with Session(engine) as session:
        _lock_user_numbers(session)
        sequence = _last_sequence(session, prefix)
        users = session.exec(
            select(UserInfo)
            .where(UserInfo.user_no.is_(None))
            .order_by(UserInfo.create_time, UserInfo.user_id)
        ).all()
        for user in users:
            sequence += 1
            user.user_no = _format_user_no(prefix, sequence)
            session.add(user)
        session.commit()
        return len(users)
