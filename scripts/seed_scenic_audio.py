"""按仓库自带的 16 段讲解音频，补齐/更新数据库中的讲解记录。

用法（项目根目录）：
    python scripts/seed_scenic_audio.py

说明：
- 数据库连接自动读取项目根目录 .env（POSTGRES_*）；
- 音频文件来自 static/tour_files/scenic-audio 下形如 {spot_id}-{revision}.wav 的文件；
- 已存在的记录按文件名/时长/讲解稿更新，不重复插入；
- 顺带删除历史测试景点「智远楼」及其录音记录。
"""
import os
import re
import sys
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402
from sqlmodel import Session, SQLModel, create_engine, select  # noqa: E402

load_dotenv(ROOT / '.env', override=True)

from server.base.models.scenic_audio import ScenicAudio  # noqa: E402
from server.base.models.tour_models import ScenicSpotInfo  # noqa: E402
from server.base.modules.scenic_narration import narration_text  # noqa: E402

AUDIO_DIR = ROOT / 'static' / 'tour_files' / 'scenic-audio'
PATTERN = re.compile(r'^(\d+)-([0-9a-f]{64})\.wav$', re.IGNORECASE)
REMOVED_SPOT_NAMES = ('智远楼', '慧智楼')


def database_url():
    password = os.getenv('POSTGRES_PASSWORD')
    if not password:
        raise SystemExit('.env 缺少 POSTGRES_PASSWORD，请先按 .env.example 配置数据库')
    return ('postgresql+psycopg://'
            + os.getenv('POSTGRES_USER', 'postgres') + ':' + password
            + '@' + os.getenv('POSTGRES_SERVER', '127.0.0.1')
            + ':' + os.getenv('POSTGRES_PORT', '15432')
            + '/' + os.getenv('POSTGRES_DB', 'streamer_sales_db'))


def audio_duration(path):
    with wave.open(str(path), 'rb') as handle:
        return round(handle.getnframes() / float(handle.getframerate()), 1)


def main():
    engine = create_engine(database_url())
    SQLModel.metadata.create_all(engine)
    files = []
    if AUDIO_DIR.is_dir():
        for path in sorted(AUDIO_DIR.glob('*.wav')):
            matched = PATTERN.match(path.name)
            if matched:
                files.append((int(matched.group(1)), matched.group(2).lower(), path))
    if not files:
        raise SystemExit('没有找到讲解音频：static/tour_files/scenic-audio/*.wav')

    created = updated = skipped = 0
    removed_spots = []
    with Session(engine) as session:
        existing_records = {row.spot_id: row for row in session.exec(select(ScenicAudio)).all()}
        for spot_id, revision, path in files:
            spot = session.get(ScenicSpotInfo, spot_id)
            if not spot or spot.delete:
                print('跳过：数据库没有景点 %d（%s）' % (spot_id, path.name))
                skipped += 1
                continue
            duration = audio_duration(path)
            script_text = narration_text(spot)
            record = existing_records.get(spot_id)
            if record is None:
                record = ScenicAudio(spot_id=spot_id, revision=revision, guide_id=1,
                                     script=script_text, file_name=path.name,
                                     duration=duration, source='xingyun-recording')
                session.add(record)
                created += 1
                continue
            changed = (record.revision != revision or record.file_name != path.name
                       or record.duration != duration or record.script != script_text)
            if changed:
                record.revision = revision
                record.file_name = path.name
                record.duration = duration
                record.script = script_text
                record.source = record.source or 'xingyun-recording'
                session.add(record)
                updated += 1
        for name in REMOVED_SPOT_NAMES:
            rows = session.exec(select(ScenicSpotInfo).where(ScenicSpotInfo.spot_name == name)).all()
            for spot in rows:
                record = session.get(ScenicAudio, spot.spot_id)
                if record:
                    session.delete(record)
                session.delete(spot)
                removed_spots.append('%s(#%d)' % (spot.spot_name, spot.spot_id))
        session.commit()

    print('讲解记录：新增 %d 条，更新 %d 条，跳过 %d 条。' % (created, updated, skipped))
    if removed_spots:
        print('已删除测试景点：' + '、'.join(removed_spots))
    print('完成。可用「听讲解」或 scripts/verify_scenic_audio.py 验证。')


if __name__ == '__main__':
    main()
