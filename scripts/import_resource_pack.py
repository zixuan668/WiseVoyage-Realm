"""Import an extracted resource pack into an initialized local database.

Usage: python scripts/import_resource_pack.py path/to/extracted-pack
Existing records and files are preserved. Application credentials are not included.
"""
import argparse
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import DateTime, MetaData, Table, URL, create_engine, select

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from server.base.models.tour_models import DigitalGuideInfo

TABLES = {
    'scenic_spot_info': ('spot_id', 'spot_name'),
    'tour_route': ('route_id', 'name'),
    'digital_guide_info': ('guide_id', 'name'),
    'knowledge_document': ('doc_id', 'content_hash'),
    'tour_route_spot': ('id', None),
}


def contained(root, relative):
    result = (root / relative).resolve()
    if not result.is_relative_to(root.resolve()):
        raise ValueError('Unsafe resource path')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pack', type=Path)
    args = parser.parse_args()
    pack = args.pack.resolve()
    payload = json.loads((pack / 'resources.json').read_text(encoding='utf-8'))
    if set(payload['tables']) != set(TABLES):
        raise ValueError('Unexpected data tables')
    # Check every file before making any changes.
    for relative, digest in payload['files'].items():
        if not relative.startswith('static/'):
            raise ValueError('Only static assets are permitted')
        source = contained(pack, relative)
        if hashlib.sha256(source.read_bytes()).hexdigest() != digest:
            raise ValueError('Resource checksum mismatch: ' + relative)
        destination = contained(ROOT, relative)
        if destination.exists() and hashlib.sha256(destination.read_bytes()).hexdigest() != digest:
            raise ValueError('Existing resource differs; refusing overwrite: ' + relative)
    load_dotenv(ROOT / '.env', override=True)
    engine = create_engine(URL.create('postgresql+psycopg',
        username=os.getenv('POSTGRES_USER', 'postgres'), password=os.environ['POSTGRES_PASSWORD'],
        host=os.getenv('POSTGRES_SERVER', '127.0.0.1'), port=int(os.getenv('POSTGRES_PORT', '15432')),
        database=os.getenv('POSTGRES_DB', 'streamer_sales_db')))
    metadata = MetaData()
    tables = {name: Table(name, metadata, autoload_with=engine) for name in TABLES}
    users = Table('user_info', metadata, autoload_with=engine)
    maps = {}
    with engine.begin() as db:
        owner = db.execute(select(users.c.user_id).where(
            users.c.username == os.getenv('ADMIN_USERNAME', 'admin'), users.c.delete == False)).scalar_one_or_none()
        if owner is None:
            raise ValueError('Start the backend first to initialize the configured administrator')
        for name, (pk, match) in TABLES.items():
            table = tables[name]
            maps[name] = {}
            for original in payload['tables'][name]:
                row = {k: v for k, v in original.items() if k in table.c and k != pk}
                if 'user_id' in table.c:
                    row['user_id'] = owner
                if name == 'digital_guide_info':
                    for field, definition in DigitalGuideInfo.model_fields.items():
                        if field in table.c and field != pk and not definition.is_required():
                            if field not in row or (row[field] is None and not table.c[field].nullable):
                                row[field] = definition.get_default(call_default_factory=True)
                    row['is_enabled'] = False  # Credentials must be supplied by the recipient.
                if name == 'knowledge_document':
                    row['status'] = 'pending'
                    row['chunk_count'] = 0
                for col in table.c:
                    if isinstance(col.type, DateTime) and isinstance(row.get(col.name), str):
                        row[col.name] = datetime.fromisoformat(row[col.name])
                if name == 'tour_route_spot':
                    row['route_id'] = maps['tour_route'][row['route_id']]
                    row['spot_id'] = maps['scenic_spot_info'][row['spot_id']]
                    condition = (table.c.route_id == row['route_id']) & (table.c.spot_id == row['spot_id'])
                else:
                    condition = table.c[match] == row[match]
                existing = db.execute(select(table.c[pk]).where(condition)).scalar_one_or_none()
                if existing is None:
                    existing = db.execute(table.insert().values(**row).returning(table.c[pk])).scalar_one()
                maps[name][original[pk]] = existing
            print(name, len(maps[name]), 'records processed')
        for relative in payload['files']:
            destination = contained(ROOT, relative)
            destination.parent.mkdir(parents=True, exist_ok=True)
            if not destination.exists():
                shutil.copy2(contained(pack, relative), destination)
    print('Import complete. Bind your digital human application and publish it in the admin UI.')


if __name__ == '__main__':
    main()
