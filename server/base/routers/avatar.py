import httpx
import asyncio
import json
from pathlib import Path
import uuid
import hmac
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlmodel import Session, select
from ...web_configs import WEB_CONFIGS
from ..database.init_db import DB_ENGINE
from ..models.avatar_job import AvatarJob
from ..models.motion_job import MotionJob
from ..modules import motion_provider
from ..modules.avatar_runtime import local_asset
from pydantic import BaseModel, Field as InputField
from ..models.tour_models import DigitalGuideInfo
from ..modules.avatar_runtime import capability
from ..utils import ResultCode, make_return_data
from .users import get_current_user_info

router = APIRouter(prefix='/avatar', tags=['avatar'])
_motion_refresh_lock = asyncio.Lock()


@router.get('/capabilities/{guide_id}')
async def capabilities(guide_id: int):
    with Session(DB_ENGINE) as db:
        guide = db.get(DigitalGuideInfo, guide_id)
    if not guide or guide.delete:
        raise HTTPException(404, '导游不存在')
    return make_return_data(True, ResultCode.SUCCESS, '成功', await capability(guide))


@router.post('/source/{guide_id}')
async def upload_source(guide_id: int, file: UploadFile = File(...), user_id: int = Depends(get_current_user_info)):
    with Session(DB_ENGINE) as db:
        guide = db.exec(select(DigitalGuideInfo).where(DigitalGuideInfo.guide_id == guide_id, DigitalGuideInfo.user_id == user_id, DigitalGuideInfo.delete == False)).first()
        if not guide:
            raise HTTPException(404, '导游不存在或无权修改')
    if Path(file.filename or '').suffix.lower() != '.mp4':
        raise HTTPException(400, '请上传 MP4 格式的正面人物视频')
    relative = Path('digital_guide') / 'sources' / (uuid.uuid4().hex + '.mp4')
    target = Path(WEB_CONFIGS.SERVER_FILE_ROOT) / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    try:
        with target.open('wb') as output:
            while chunk := await file.read(1024 * 1024):
                total += len(chunk)
                if total > 200 * 1024 * 1024:
                    raise HTTPException(413, '视频不能超过 200MB')
                output.write(chunk)
        with target.open('rb') as source:
            signature = source.read(12)
        if total < 12 or signature[4:8] != b'ftyp':
            raise HTTPException(400, '文件不是有效的 MP4 视频')
        from ..modules.video_inspection import inspect_video
        try:
            metadata = await asyncio.to_thread(inspect_video, target)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        with Session(DB_ENGINE) as db:
            guide = db.get(DigitalGuideInfo, guide_id)
            if not guide or guide.delete or guide.user_id != user_id:
                raise HTTPException(404, '导游不存在或无权修改')
            guide.base_video_metadata = json.dumps(metadata, ensure_ascii=False)
            guide.base_mp4_path = relative.as_posix()
            db.add(guide)
            db.commit()
        return make_return_data(True, ResultCode.SUCCESS, '动作素材已校验并保存', {'path': relative.as_posix(), 'metadata': metadata})
    except Exception:
        target.unlink(missing_ok=True)
        raise
    finally:
        await file.close()


@router.get('/jobs/{job_id}')
async def get_job(job_id: str, token: str):
    with Session(DB_ENGINE) as db:
        job = db.get(AvatarJob, job_id)
        if not job or not hmac.compare_digest(job.access_token, token):
            raise HTTPException(404, '任务不存在')
        data = {'job_id': job.job_id, 'status': job.status, 'video_url': job.video_url, 'message': job.error}
    return make_return_data(True, ResultCode.SUCCESS, '成功', data)


class MotionRequest(BaseModel):
    prompt: str = InputField(default=motion_provider.DEFAULT_PROMPT, min_length=1, max_length=800)


def owned_guide(db, guide_id, user_id):
    guide = db.exec(select(DigitalGuideInfo).where(DigitalGuideInfo.guide_id == guide_id,
                    DigitalGuideInfo.user_id == user_id, DigitalGuideInfo.delete == False).with_for_update()).first()
    if not guide:
        raise HTTPException(404, '导游不存在或无权修改')
    return guide


def motion_data(job):
    return {'job_id': job.job_id, 'status': job.status, 'prompt': job.prompt, 'message': job.error,
            'video_url': '/api/v1/files/'+job.video_path if job.video_path else '',
            'metadata': json.loads(job.video_metadata or '{}')}


@router.get('/motion-config')
async def motion_config(user_id: int = Depends(get_current_user_info)):
    return make_return_data(True, ResultCode.SUCCESS, '成功', {'configured': motion_provider.configured(),
        'model': 'wan2.2-i2v-plus', 'default_prompt': motion_provider.DEFAULT_PROMPT,
        'message': '服务已配置，生成将调用收费接口' if motion_provider.configured() else '待配置：后端缺少 DASHSCOPE_API_KEY'})


@router.post('/motion/{guide_id}')
async def create_motion(guide_id: int, data: MotionRequest, user_id: int = Depends(get_current_user_info)):
    if not motion_provider.configured():
        raise HTTPException(503, '动作生成待配置：请在后端 .env 配置 DASHSCOPE_API_KEY')
    with Session(DB_ENGINE) as db:
        guide = owned_guide(db, guide_id, user_id)
        active = db.exec(select(MotionJob).where(MotionJob.guide_id == guide_id,
                        MotionJob.status.in_(['submitting', 'pending', 'running', 'unknown']))).first()
        if active:
            return make_return_data(True, ResultCode.SUCCESS, '已有任务，请查询原任务', motion_data(active))
        image = local_asset(guide.poster_image or guide.avatar)
        if not image:
            raise HTTPException(400, '请先上传本地角色海报')
        job = MotionJob(job_id=uuid.uuid4().hex, guide_id=guide_id, user_id=user_id, prompt=data.prompt,
                        source_image=guide.poster_image or guide.avatar, previous_source=guide.base_mp4_path)
        db.add(job); db.commit(); db.refresh(job)
    try:
        task = await motion_provider.submit(image, data.prompt)
        status, error = 'pending', ''
    except (httpx.TimeoutException, httpx.TransportError):
        task, status, error = '', 'unknown', '提交结果不确定，请在百炼控制台核对，避免重复计费'
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code >= 500:
            task, status, error = '', 'unknown', '服务异常，提交结果不确定，请在百炼控制台核对，避免重复计费'
        else:
            task, status, error = '', 'failed', '服务拒绝任务，请检查密钥、地域、余额和海报格式'
    except ValueError:
        task, status, error = '', 'failed', '服务未接受任务，请检查海报格式和服务配置'
    with Session(DB_ENGINE) as db:
        job = db.get(MotionJob, job.job_id)
        job.provider_task_id, job.status, job.error = task, status, error
        db.add(job); db.commit(); db.refresh(job)
        return make_return_data(True, ResultCode.SUCCESS, '任务状态已保存', motion_data(job))


@router.get('/motion/{guide_id}')
async def latest_motion(guide_id: int, user_id: int = Depends(get_current_user_info)):
    with Session(DB_ENGINE) as db:
        owned_guide(db, guide_id, user_id)
        job = db.exec(select(MotionJob).where(MotionJob.guide_id == guide_id,
                         MotionJob.user_id == user_id).order_by(MotionJob.created_at.desc())).first()
        return make_return_data(True, ResultCode.SUCCESS, '成功', motion_data(job) if job else None)


@router.post('/motion-jobs/{job_id}/refresh')
async def refresh_motion(job_id: str, user_id: int = Depends(get_current_user_info)):
    async with _motion_refresh_lock:
        with Session(DB_ENGINE) as db:
            job = db.get(MotionJob, job_id)
            if not job or job.user_id != user_id:
                raise HTTPException(404, '任务不存在')
            owned_guide(db, job.guide_id, user_id)
            if job.status not in ('pending', 'running'):
                return make_return_data(True, ResultCode.SUCCESS, '成功', motion_data(job))
            db.expunge(job)
        try:
            result = await motion_provider.query(job.provider_task_id)
            state = result.get('task_status')
            if state == 'SUCCEEDED':
                relative = 'digital_guide/sources/motion-'+job.job_id+'.mp4'
                target = Path(WEB_CONFIGS.SERVER_FILE_ROOT)/relative
                if not target.is_file():
                    await motion_provider.download(result.get('video_url', ''), target)
                from ..modules.video_inspection import inspect_video
                metadata = await asyncio.to_thread(inspect_video, target)
                metadata['provider'] = 'wan2.2-i2v-plus'
                job.video_path, job.video_metadata, job.status = relative, json.dumps(metadata, ensure_ascii=False), 'completed'
                job.error = ''
            elif state in ('FAILED', 'CANCELED', 'UNKNOWN'):
                job.status, job.error = 'failed', '视频生成失败：'+str(result.get('code', state))
            elif state in ('PENDING', 'RUNNING'):
                job.status = 'pending' if state == 'PENDING' else 'running'
            else:
                raise ValueError('服务返回未知任务状态')
        except ValueError as exc:
            job.status, job.error = 'failed', str(exc)
        except httpx.HTTPError:
            raise HTTPException(502, '查询或转存失败，请稍后刷新原任务')
        with Session(DB_ENGINE) as db:
            db.add(job); db.commit(); db.refresh(job)
            return make_return_data(True, ResultCode.SUCCESS, '成功', motion_data(job))


@router.post('/motion-jobs/{job_id}/apply')
async def apply_motion(job_id: str, user_id: int = Depends(get_current_user_info)):
    with Session(DB_ENGINE) as db:
        job = db.get(MotionJob, job_id)
        if not job or job.user_id != user_id:
            raise HTTPException(404, '任务不存在')
        guide = owned_guide(db, job.guide_id, user_id)
        if job.status not in ('completed', 'applied') or not local_asset(job.video_path):
            raise HTTPException(409, '动作视频尚未生成或文件不存在')
        if guide.base_mp4_path == job.video_path:
            return make_return_data(True, ResultCode.SUCCESS, '已应用', motion_data(job))
        if guide.base_mp4_path != job.previous_source or (guide.poster_image or guide.avatar) != job.source_image:
            raise HTTPException(409, '角色素材已改变，请重新生成，防止覆盖新配置')
        guide.base_mp4_path, guide.base_video_metadata = job.video_path, job.video_metadata
        job.status = 'applied'
        db.add(guide); db.add(job); db.commit(); db.refresh(job)
        return make_return_data(True, ResultCode.SUCCESS, '已应用，导览将保留全身动作并生成本轮口型', motion_data(job))


class MotionRecovery(BaseModel):
    task_id: str = InputField(pattern=r'^[A-Za-z0-9_-]{1,96}$')


@router.post('/motion-jobs/{job_id}/recover')
async def recover_motion(job_id: str, data: MotionRecovery, user_id: int = Depends(get_current_user_info)):
    with Session(DB_ENGINE) as db:
        job = db.get(MotionJob, job_id)
        if not job or job.user_id != user_id:
            raise HTTPException(404, '任务不存在')
        owned_guide(db, job.guide_id, user_id)
        if job.status != 'unknown':
            raise HTTPException(409, '仅提交结果不确定的任务可恢复')
    try:
        result = await motion_provider.query(data.task_id)
    except (httpx.HTTPError, ValueError):
        raise HTTPException(502, '查询百炼任务失败，请检查任务ID和密钥')
    if result.get('task_status') not in ('PENDING', 'RUNNING', 'SUCCEEDED', 'FAILED', 'CANCELED'):
        raise HTTPException(400, '无法找到有效的百炼任务')
    with Session(DB_ENGINE) as db:
        job = db.get(MotionJob, job_id)
        if job.status != 'unknown':
            raise HTTPException(409, '任务状态已改变，请刷新')
        job.provider_task_id, job.status, job.error = data.task_id, 'pending', ''
        db.add(job); db.commit()
    return await refresh_motion(job_id, user_id)
