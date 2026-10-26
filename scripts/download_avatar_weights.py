"""Download only the weights used by this project's MuseTalk 1.0 adapter."""
import os
import hashlib
import time
import requests
from pathlib import Path
from urllib.request import urlretrieve
from huggingface_hub import hf_hub_download


def stream_download(url, path, expected_hash=None):
    path = Path(path)
    if path.is_file():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.part')
    for attempt in range(3):
        start = temporary.stat().st_size if temporary.exists() else 0
        try:
            with requests.get(url, headers={'Range': f'bytes={start}-'} if start else {}, stream=True, timeout=(20, 60)) as response:
                response.raise_for_status()
                if response.status_code != 206:
                    start = 0
                total = start + int(response.headers.get('Content-Length', 0))
                received = start
                checkpoint = start
                with temporary.open('ab' if start else 'wb') as target:
                    for chunk in response.iter_content(1024 * 1024):
                        target.write(chunk)
                        received += len(chunk)
                        if received - checkpoint >= 64 * 1024 * 1024:
                            print(f'{path.name}: {received // 1048576} / {total // 1048576} MiB', flush=True)
                            checkpoint = received
                if total and received != total:
                    raise IOError('下载大小与服务器声明不一致')
            if expected_hash:
                digest = hashlib.sha256()
                with temporary.open('rb') as source:
                    for chunk in iter(lambda: source.read(1024 * 1024), b''):
                        digest.update(chunk)
                if digest.hexdigest() != expected_hash:
                    raise ValueError('模型 SHA256 不匹配，不能加载')
            temporary.replace(path)
            return
        except (requests.RequestException, IOError):
            if attempt == 2:
                raise
            time.sleep(2)

root = Path(__file__).resolve().parents[1] / 'weights/digital_human_weights'
endpoint = os.environ.get('HF_ENDPOINT', 'https://huggingface.co')
files = [
    ('TMElyralab/MuseTalk', 'musetalk/musetalk.json', root),
    ('TMElyralab/MuseTalk', 'musetalk/pytorch_model.bin', root),
    ('stabilityai/sd-vae-ft-mse', 'config.json', root / 'sd-vae-ft-mse'),
    ('stabilityai/sd-vae-ft-mse', 'diffusion_pytorch_model.bin', root / 'sd-vae-ft-mse'),
    ('yzd-v/DWPose', 'dw-ll_ucoco_384.pth', root / 'dwpose'),
    ('ManyOtherFunctions/face-parse-bisent', '79999_iter.pth', root / 'face-parse-bisent'),
]
for repo, filename, directory in files:
    print(f'Downloading {repo}/{filename}', flush=True)
    if endpoint != 'https://huggingface.co':
        expected = '0ee7d5ea03ea75d8dca50ea7a76df791e90633687a135c4a69393abfc0475ffe' if repo == 'TMElyralab/MuseTalk' and filename.endswith('.bin') else None
        stream_download(f'{endpoint}/{repo}/resolve/main/{filename}', directory / filename, expected)
    else:
        hf_hub_download(repo, filename, local_dir=str(directory), endpoint=endpoint)
urls = [
    ('https://download.pytorch.org/models/resnet18-5c106cde.pth', root / 'face-parse-bisent/resnet18-5c106cde.pth'),
    ('https://openaipublic.azureedge.net/main/whisper/models/65147644a518d12f04e32d6f3b26facc3f8dd46e5390956a9424a650c0ce22b9/tiny.pt', root / 'whisper/tiny.pt'),
]
for url, path in urls:
    if path.is_file():
        continue
    path.parent.mkdir(parents=True, exist_ok=True)
    print(f'Downloading {path.name}', flush=True)
    stream_download(url, path)
print('All required weight files downloaded.', flush=True)
