"""Record actual Xingyun narration for all active scenic spots. Run from repo root.

Requires Node playwright-core and installed Chrome. Credentials stay in Python;
the localhost-only browser bridge uses a fresh secret and is stopped afterwards.
"""
import argparse
import asyncio
import json
import os
from pathlib import Path
import secrets
import socket
import struct
import subprocess
import sys
import threading

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv
load_dotenv(ROOT / '.env')
import httpx
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse
from sqlmodel import Session, select
from server.base.database.init_db import DB_ENGINE
from server.base.models.tour_models import ScenicSpotInfo, DigitalGuideInfo
from server.base.models.xingyun import XingyunGuideBinding
from server.base.models.scenic_audio import ScenicAudio
from server.base.modules.scenic_narration import narration_text, narration_revision, voice_identity, recording_file
from server.base.modules.xingyun_access import decrypt_secret
from server.base.routers.xingyun import GATEWAY, signed_headers
from server.web_configs import WEB_CONFIGS


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--guide-id', type=int, default=1)
    parser.add_argument('--spot-id', type=int)
    args = parser.parse_args()
    token = secrets.token_urlsafe(32)
    output = ROOT / WEB_CONFIGS.SERVER_FILE_ROOT / WEB_CONFIGS.TOUR_FILE_DIR / 'scenic-audio'
    output.mkdir(parents=True, exist_ok=True)
    ScenicAudio.__table__.create(DB_ENGINE, checkfirst=True)
    with Session(DB_ENGINE) as db:
        guide = db.get(DigitalGuideInfo, args.guide_id)
        binding = db.get(XingyunGuideBinding, args.guide_id)
        if not guide or guide.delete or not binding:
            raise RuntimeError('指定数字人不存在或未绑定星云')
        identity = voice_identity(binding)
        app_id, secret = binding.app_id, decrypt_secret(binding.secret_encrypted)
        spots = db.exec(select(ScenicSpotInfo).where(ScenicSpotInfo.delete == False).order_by(ScenicSpotInfo.spot_id)).all()
        jobs = []
        for spot in spots:
            if args.spot_id and args.spot_id != spot.spot_id: continue
            script = narration_text(spot)
            if not script: continue
            revision = narration_revision(script, identity)
            old = db.get(ScenicAudio, spot.spot_id)
            if old and old.revision == revision and recording_file(output, old): continue
            jobs.append(dict(id=spot.spot_id, name=spot.spot_name, script=script, revision=revision))
    if not jobs:
        print('所有景点均已有最新录音'); return
    app = FastAPI()
    sessions = {}
    saved = []

    @app.middleware('http')
    async def protect(request, call_next):
        from fastapi.responses import Response
        if request.headers.get('x-record-token') != token:
            return Response(status_code=403)
        return await call_next(request)

    @app.get('/')
    def index():
        return HTMLResponse('<html><body><div id="avatar" style="width:640px;height:720px"></div><script src="/sdk.js"></script></body></html>')

    @app.get('/sdk.js')
    def sdk():
        return FileResponse(ROOT / 'frontend/public/vendor/xingyun/xmov-avatar-2.4.1-compatible.js', media_type='text/javascript')

    @app.get('/jobs')
    def get_jobs(): return jobs

    @app.api_route('/session', methods=['POST', 'DELETE'])
    async def session(request: Request):
        body = await request.json()
        async with httpx.AsyncClient(timeout=60, trust_env=False) as client:
            res = await client.request(request.method, GATEWAY, json=body,
                headers=signed_headers(request.method, body, app_id=app_id, app_secret=secret))
        payload = res.json()
        data = payload.get('data') or {}
        if request.method == 'POST' and data.get('session_id'):
            sessions[str(data['session_id'])] = {'session_id':data['session_id'], 'request_id':data.get('request_id', '')}
        elif request.method == 'DELETE' and res.is_success:
            sessions.pop(str(body.get('session_id', '')), None)
        from fastapi.responses import JSONResponse
        return JSONResponse(payload, status_code=res.status_code)

    @app.post('/record/{spot_id}')
    async def save(spot_id: int, request: Request, duration: float):
        job = next((j for j in jobs if j['id'] == spot_id), None)
        if not job or not 0 < duration < 3600: raise HTTPException(422)
        audio = bytearray()
        async for chunk in request.stream():
            audio.extend(chunk)
            if len(audio) > 30_000_000: raise HTTPException(413)
        if len(audio) < 100 or audio[:4] != b'RIFF' or audio[8:12] != b'WAVE': raise HTTPException(422, '无效的 WAV 音轨')
        channels, rate, bits = struct.unpack('<H', audio[22:24])[0], struct.unpack('<I', audio[24:28])[0], struct.unpack('<H', audio[34:36])[0]
        if channels not in (1, 2) or rate < 8000 or bits != 16: raise HTTPException(422, '不支持的 WAV 音轨格式')
        actual = (len(audio) - 44) / (rate * channels * bits / 8) if len(audio) > 44 else 0
        if actual <= 0 or abs(actual - duration) > max(2.0, duration * 0.02): raise HTTPException(422, '音轨实际时长与上报不一致')
        if actual < len(job['script']) / 8: raise HTTPException(422, '录音过短，可能缺失讲解')
        filename = f"{spot_id}-{job['revision']}.wav"
        with Session(DB_ENGINE) as db:
            spot = db.get(ScenicSpotInfo, spot_id)
            current_binding = db.get(XingyunGuideBinding, args.guide_id)
            if not spot or spot.delete or not current_binding or narration_revision(narration_text(spot), voice_identity(current_binding)) != job['revision']:
                raise HTTPException(409, '录制期间景点资料发生变化')
            (output / filename).write_bytes(audio)
            record = db.get(ScenicAudio, spot_id)
            values = dict(revision=job['revision'], guide_id=args.guide_id, script=job['script'], file_name=filename, duration=duration)
            if record:
                for key, value in values.items(): setattr(record, key, value)
            else: record = ScenicAudio(spot_id=spot_id, **values)
            db.add(record); db.commit()
        saved.append(spot_id)
        print(f'已保存 {spot_id} {job["name"]} {duration:.1f}s ({len(audio)} bytes)', flush=True)
        return {'saved':True}

    sock = socket.socket()
    sock.bind(('127.0.0.1', 0))
    port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, log_level='error'))
    thread = threading.Thread(target=server.run, kwargs={'sockets':[sock]}, daemon=True)
    thread.start()
    import time
    while not server.started and thread.is_alive(): time.sleep(.05)
    try:
        result = subprocess.run(['node', str(ROOT/'scripts/record_scenic_narration.cjs'), str(port)],
            env={**os.environ, 'SCENIC_RECORD_TOKEN':token}, cwd=ROOT)
    finally:
        async def cleanup():
            async with httpx.AsyncClient(timeout=20, trust_env=False) as client:
                for body in list(sessions.values()):
                    try:
                        await client.request('DELETE', GATEWAY, json=body,
                            headers=signed_headers('DELETE', body, app_id=app_id, app_secret=secret))
                    except httpx.HTTPError: print('星云会话释放失败，请在控制台检查', flush=True)
        asyncio.run(cleanup())
        server.should_exit = True
        thread.join(timeout=10)
        sock.close()
    print(f'本次保存 {len(saved)}/{len(jobs)} 个景点完整录音')
    if result.returncode or len(saved) != len(jobs): raise SystemExit(1)


if __name__ == '__main__': main()
