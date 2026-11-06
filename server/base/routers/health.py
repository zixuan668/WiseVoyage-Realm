"""Small readiness probe: no credentials, external calls or database changes."""
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

router = APIRouter()

@router.get('/health/live', include_in_schema=False)
def live():
    return {'status': 'alive'}

def probe_database():
    from ..database.init_db import DB_ENGINE
    with DB_ENGINE.connect() as connection:
        connection.execute(text('SELECT 1'))
        return connection.execute(text('SELECT count(*) FROM scenic_spot_info WHERE "delete" = FALSE')).scalar()

def rag_available():
    from ..server_info import SERVER_PLUGINS_INFO
    return SERVER_PLUGINS_INFO.rag_enabled

@router.get('/health/ready', include_in_schema=False)
def ready():
    try:
        count = probe_database()
    except Exception:
        return JSONResponse({'status': 'not_ready', 'database': 'unavailable',
                             'message': '数据库连接或表结构异常，请检查配置与初始化日志。'}, status_code=503)
    if not count:
        return JSONResponse({'status': 'not_ready', 'database': 'connected', 'scenic_spots': 0,
                             'message': '数据库已连接，但尚未导入景点内容包。'}, status_code=503)
    return {'status': 'ready', 'database': 'connected', 'scenic_spots': count,
            'rag': 'available' if rag_available() else 'unavailable'}
