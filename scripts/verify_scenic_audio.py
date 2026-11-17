"""只读核对 17 个景点的完整讲解录音：数据库记录、版本、文件、时长与内容一致性。

用法：python scripts/verify_scenic_audio.py
不连接星云、不写数据库、不修改文件；仅在本机读取 static/tour_files/scenic-audio 下的 WAV 头。
"""
import sys
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv
load_dotenv(ROOT / '.env')
from sqlmodel import Session, select
from server.base.database.init_db import DB_ENGINE
from server.base.models.tour_models import ScenicSpotInfo
from server.base.models.xingyun import XingyunGuideBinding
from server.base.models.scenic_audio import ScenicAudio
from server.base.modules.scenic_narration import narration_text, narration_revision, voice_identity, recording_file
from server.web_configs import WEB_CONFIGS


def main() -> int:
    directory = ROOT / WEB_CONFIGS.SERVER_FILE_ROOT / WEB_CONFIGS.TOUR_FILE_DIR / 'scenic-audio'
    problems = []
    with Session(DB_ENGINE) as db:
        spots = db.exec(select(ScenicSpotInfo).where(ScenicSpotInfo.delete == False)
                        .order_by(ScenicSpotInfo.spot_id)).all()
        binding = db.get(XingyunGuideBinding, 1)
        identity = voice_identity(binding) if binding else None
        rows = []
        for spot in spots:
            script = narration_text(spot)
            if not script:
                problems.append(f'景点 {spot.spot_id} 讲稿为空，未生成录音')
                rows.append((spot.spot_id, spot.spot_name, 0, 0.0, 0.0, 'NO-SCRIPT'))
                continue
            revision = narration_revision(script, identity) if identity else None
            record = db.get(ScenicAudio, spot.spot_id)
            status, duration, rate = 'MISSING', 0.0, 0
            if record:
                if not identity:
                    status = 'NO-BINDING'
                elif record.revision != revision:
                    status = 'STALE'
                elif not recording_file(directory, record):
                    status = 'NO-FILE'
                else:
                    path = directory / record.file_name
                    try:
                        with wave.open(str(path), 'rb') as wav:
                            rate = wav.getframerate()
                            frames = wav.getnframes()
                            duration = frames / rate if rate else 0.0
                            width = wav.getsampwidth()
                            peak = 0
                            remaining = frames
                            while remaining > 0:
                                chunk = wav.readframes(min(remaining, 20000))
                                if not chunk:
                                    break
                                step = 400 if width == 2 else 20000
                                for index in range(0, len(chunk) - width + 1, step * width):
                                    value = int.from_bytes(chunk[index:index + width], 'little', signed=True)
                                    peak = max(peak, abs(value))
                                remaining -= 20000
                            if peak < 300:
                                status = 'SILENT'
                                problems.append(f'景点 {spot.spot_id} 录音接近静音，峰值 {peak}')
                    except wave.Error as error:
                        status = 'BAD-WAV'
                        problems.append(f'景点 {spot.spot_id} WAV 头无法解析：{error}')
                    else:
                        if abs(duration - record.duration) > max(2.0, record.duration * 0.02):
                            status = 'DUR-MISMATCH'
                            problems.append(f'景点 {spot.spot_id} 文件时长 {duration:.1f}s 与数据库 {record.duration:.1f}s 不一致')
                        elif duration < len(script) / 10 or duration > len(script) / 2 + 30:
                            status = 'DUR-IMPLAUSIBLE'
                            problems.append(f'景点 {spot.spot_id} 时长 {duration:.1f}s 与讲稿 {len(script)} 字不匹配')
                        else:
                            status = 'OK'
            rows.append((spot.spot_id, spot.spot_name, len(script), duration, rate, status))
            if status in ('MISSING', 'NO-BINDING', 'STALE', 'NO-FILE', 'BAD-WAV') and record is None:
                problems.append(f'景点 {spot.spot_id} {spot.spot_name} 尚未生成录音')
            elif status in ('STALE', 'NO-FILE', 'BAD-WAV'):
                problems.append(f'景点 {spot.spot_id} {spot.spot_name} 录音不可用：{status}')
    print(f'{"ID":>3}  {"景点":<10} {"字数":>4} {"时长(s)":>8} {"采样率":>6}  状态')
    for spot_id, name, chars, duration, rate, status in rows:
        print(f'{spot_id:>3}  {name:<10} {chars:>4} {duration:>8.1f} {rate:>6}  {status}')
    ok = sum(1 for row in rows if row[5] == 'OK')
    print(f'\n完整录音 {ok}/{len(rows)} 个景点')
    if problems:
        print('待处理：')
        for problem in problems:
            print(' -', problem)
    return 0 if ok == len(rows) and rows else 1


if __name__ == '__main__':
    raise SystemExit(main())
