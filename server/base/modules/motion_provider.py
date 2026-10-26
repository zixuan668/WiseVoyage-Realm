"""Wan asynchronous image-to-video integration. Credentials stay on the server."""
import base64
import os
from urllib.parse import urlparse
import httpx

DEFAULT_PROMPT = '固定镜头，全身人物始终完整入镜，保持参考图的人脸、发型、服装和背景一致。人物面向镜头温柔微笑，自然呼吸，轻轻点头，一只手缓慢抬起做欢迎和讲解手势，再放回原位。动作小幅、流畅，双脚位置稳定。头部保持正面，嘴部不主动说话。结尾回到开始站姿，无镜头推拉、无切换。'


def settings():
    key = os.getenv('DASHSCOPE_API_KEY', '').strip()
    base = os.getenv('MOTION_API_BASE', 'https://dashscope.aliyuncs.com/api/v1').rstrip('/')
    host = urlparse(base).hostname or ''
    if not base.startswith('https://') or not (host == 'dashscope.aliyuncs.com' or host.endswith('.maas.aliyuncs.com')):
        raise ValueError('MOTION_API_BASE 须为百炼官方 HTTPS API 地址')
    return key, base


def configured():
    try:
        return bool(settings()[0])
    except ValueError:
        return False


async def submit(image, prompt):
    key, base = settings()
    content = image.read_bytes()
    if len(content) > 10 * 1024 * 1024:
        raise ValueError('海报超过10MB，请先压缩')
    mime = 'image/png' if content.startswith(b'\x89PNG') else 'image/jpeg' if content.startswith(b'\xff\xd8') else ''
    if not mime:
        raise ValueError('海报须为PNG或JPEG')
    payload = {'model': 'wan2.2-i2v-plus', 'input': {'img_url': 'data:'+mime+';base64,'+base64.b64encode(content).decode(),
               'prompt': prompt, 'negative_prompt': '镜头移动，半身裁切，换脸，换装，背景变化，夸张动作，多余手指，身体畸形'},
               'parameters': {'resolution': '1080P', 'prompt_extend': False, 'watermark': True}}
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(base+'/services/aigc/video-generation/video-synthesis', json=payload,
                        headers={'Authorization': 'Bearer '+key, 'X-DashScope-Async': 'enable'})
        response.raise_for_status()
        data = response.json()
    task = data.get('output', {}).get('task_id')
    if not task:
        raise ValueError('服务未接受任务：'+str(data.get('code', 'Unknown')))
    return task


async def query(task):
    key, base = settings()
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(base+'/tasks/'+task, headers={'Authorization': 'Bearer '+key})
        response.raise_for_status()
        return response.json().get('output', {})


async def download(url, target):
    parsed = urlparse(url)
    if parsed.scheme != 'https' or not ((parsed.hostname or '').endswith('.aliyuncs.com') or (parsed.hostname or '').endswith('.alicdn.com')):
        raise ValueError('服务返回的视频地址不是受支持的阿里云 HTTPS 地址')
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream('GET', url) as response:
                response.raise_for_status()
                total = 0
                with target.open('wb') as output:
                    async for chunk in response.aiter_bytes():
                        total += len(chunk)
                        if total > 200 * 1024 * 1024:
                            raise ValueError('生成视频超过200MB')
                        output.write(chunk)
    except Exception:
        target.unlink(missing_ok=True)
        raise
