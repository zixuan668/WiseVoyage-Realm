"""Read-only checks for the three-client Summer Palace handover snapshot."""
import argparse
import hashlib
import json
import re
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
COUNTS = {'scenic_spot_info': 16, 'tour_route': 3, 'digital_guide_info': 2, 'knowledge_document': 24}
LEGACY_TABLES = {'chat_message_info', 'on_air_room_status_item', 'sales_doc_and_video_info',
                 'stream_room_info', 'streamer_info', 'product_info'}


def check_files():
    for name in ['frontend/src/router/index.ts', 'app/pages.json', 'server/base/base_server.py',
                 'shared/coordinates.js', 'data/summer_palace_walk_network.json', 'LICENSE']:
        assert (ROOT / name).is_file(), f'Missing required delivery file: {name}'
    # uni-app pages.json supports comments; native compilation validates the
    # full document, while this check validates each registered page path.
    pages = re.findall(r'"path"\s*:\s*"([^"]+)"', (ROOT / 'app/pages.json').read_text(encoding='utf-8-sig'))
    assert pages, 'No registered App pages'
    for page in pages:
        assert (ROOT / 'app' / (page + '.vue')).is_file(), f'Missing App page: {page}'
    for name in ['server/asr', 'server/tts', 'server/base/models/product_model.py',
                 'server/base/models/streamer_room_model.py', 'app/components/TabBarNav.vue',
                 'app/pages/favorites', 'app/pages/rank', 'frontend/public/onboarding']:
        assert not (ROOT / name).exists(), f'Retired content remains: {name}'
    archive = ROOT / 'resources/summer-palace-content.zip'
    expected = (ROOT / 'resources/summer-palace-content.sha256').read_text().split()[0]
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == expected, 'Content archive checksum mismatch'
    with zipfile.ZipFile(archive) as bundle:
        assert bundle.testzip() is None, 'Corrupted content archive'
        manifests = [name for name in bundle.namelist() if name.endswith('/resources.json')]
        assert len(manifests) == 1
        prefix = manifests[0][:-len('resources.json')]
        manifest = json.loads(bundle.read(manifests[0]))
        assert not any(Path(name).name == '.env' or name.endswith('.dump') for name in bundle.namelist())
        for table, count in COUNTS.items():
            assert len(manifest['tables'][table]) == count, f'Unexpected content count: {table}'
        for name, checksum in manifest['files'].items():
            assert hashlib.sha256(bundle.read(prefix + name)).hexdigest() == checksum, f'Asset checksum mismatch: {name}'
    return {'app_pages': len(pages), 'public_content': COUNTS, 'archive_and_assets_verified': True}


def check_database():
    from dotenv import dotenv_values
    import psycopg
    cfg = dotenv_values(ROOT / '.env')
    with psycopg.connect(host=cfg.get('POSTGRES_SERVER', '127.0.0.1'),
                         port=int(cfg.get('POSTGRES_PORT', '25432')),
                         user=cfg.get('POSTGRES_USER', 'postgres'), password=cfg['POSTGRES_PASSWORD'],
                         dbname=cfg.get('POSTGRES_DB', 'streamer_sales_db'), connect_timeout=8,
                         options='-c default_transaction_read_only=on') as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
            assert not LEGACY_TABLES.intersection(row[0] for row in cursor.fetchall()), 'Commerce tables remain'
            for table, count in COUNTS.items():
                cursor.execute('SELECT count(*) FROM ' + table)
                assert cursor.fetchone()[0] == count, f'Database snapshot count differs: {table}'
            cursor.execute('SELECT spot_name, city, "delete" FROM scenic_spot_info')
            places = cursor.fetchall()
            catalog = json.loads((ROOT / 'data/summer_palace_knowledge.json').read_text(encoding='utf-8'))
            names = set(catalog['spots'])
            assert all(name in names and city == '北京' and not deleted for name, city, deleted in places)
    return {'database_read_only_check': 'passed', 'summer_palace_only': True, 'counts': COUNTS}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', action='store_true', help='Read the configured database without changing it')
    args = parser.parse_args()
    result = {'files': check_files()}
    if args.database:
        result['database'] = check_database()
    print(json.dumps({'passed': True, **result}, ensure_ascii=False))


if __name__ == '__main__':
    main()
