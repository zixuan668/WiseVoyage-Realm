"""Export public local content and referenced assets, never credentials or visitor data.

Usage: python scripts/export_resource_pack.py work_dirs/local-resources
The output directory must not exist. Import using scripts/import_resource_pack.py.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import zipfile
from datetime import date, datetime
from pathlib import Path
from urllib.parse import unquote, urlsplit

from dotenv import load_dotenv
from sqlalchemy import MetaData, Table, URL, create_engine, select

ROOT = Path(__file__).resolve().parents[1]
# Explicit allowlist: new database columns cannot silently enter a public export.
FIELDS = {
    'scenic_spot_info': 'spot_id spot_name category tags location city latitude longitude trigger_radius visit_duration best_season description history_detail photo_tips service_facilities tour_tips image_path instruction upload_date delete'.split(),
    'tour_route': 'route_id name theme city estimated_time_minutes cover_image cover_generated description delete'.split(),
    'digital_guide_info': 'guide_id name character avatar voice_style voice_speed language name_en character_en outfit_images tts_weight_tag tts_reference_sentence tts_reference_audio poster_image base_mp4_path base_video_metadata render_mode is_enabled delete'.split(),
    'knowledge_document': 'doc_id title file_path file_type chunk_count content_hash upload_time status'.split(),
    'tour_route_spot': 'id route_id spot_id spot_order'.split(),
}
ASSETS = {
    'scenic_spot_info': ['image_path', 'instruction'],
    'tour_route': ['cover_image'],
    'digital_guide_info': ['avatar', 'poster_image', 'base_mp4_path', 'tts_reference_audio'],
    'knowledge_document': ['file_path'],
}


def local_asset(value, root):
    """Return a contained static file, None for an external URL, reject traversal."""
    if not value:
        return None
    value = str(value).replace('\\', '/')
    parsed = urlsplit(value)
    if parsed.scheme in ('http', 'https'):
        if parsed.hostname not in ('localhost', '127.0.0.1', '::1'):
            return None
        value = unquote(parsed.path)
    elif re.match(r'^[A-Za-z]:/', value):
        source = Path(value).resolve()
        if not source.is_relative_to((root / 'static').resolve()):
            raise ValueError('Asset outside project static directory')
        return source
    else:
        value = unquote(value)
    for prefix in ('/api/v1/files/', 'api/v1/files/', '/files/', 'files/', '/static/', 'static/'):
        if value.startswith(prefix):
            value = value[len(prefix):]
            break
    source = (root / 'static' / value.lstrip('/')).resolve()
    if not source.is_relative_to((root / 'static').resolve()):
        raise ValueError('Asset path escapes static directory')
    return source


def export_pack(root, engine, output):
    root, output = root.resolve(), output.resolve()
    if output.exists():
        raise ValueError('Output already exists; choose a new directory')
    metadata = MetaData()
    payload = {'tables': {}, 'files': {}}
    # Use one snapshot so routes, their members and the catalog agree.
    with engine.connect().execution_options(isolation_level='SERIALIZABLE') as db:
        with db.begin():
            for name, fields in FIELDS.items():
                table = Table(name, metadata, autoload_with=db)
                columns = [table.c[field] for field in fields if field in table.c]
                query = select(*columns).order_by(table.c[fields[0]])
                if 'delete' in table.c:
                    query = query.where(table.c.delete == False)
                payload['tables'][name] = [dict(row) for row in db.execute(query).mappings()]
    tables = payload['tables']
    spot_ids = {row['spot_id'] for row in tables['scenic_spot_info']}
    route_ids = {row['route_id'] for row in tables['tour_route']}
    tables['tour_route_spot'] = [row for row in tables['tour_route_spot']
                               if row['route_id'] in route_ids and row['spot_id'] in spot_ids]
    sources = {}

    def add_file(source):
        if not source.is_file():
            raise FileNotFoundError('Missing referenced asset: ' + str(source.relative_to(root)))
        relative = source.relative_to(root).as_posix()
        sources[relative] = source
        return source.relative_to(root / 'static').as_posix()

    for name, rows in tables.items():
        for row in rows:
            for field in ASSETS.get(name, []):
                # Legacy scenic entries store Markdown itself instead of a file path.
                if field == 'instruction' and ('\n' in str(row.get(field, '')) or str(row.get(field, '')).startswith(('#', '**'))):
                    continue
                source = local_asset(row.get(field, ''), root)
                if source is not None:
                    row[field] = add_file(source)
            if name == 'digital_guide_info':
                row['is_enabled'] = False
                row['base_video_metadata'] = ''  # Revalidate on the receiving machine.
                outfits = json.loads(row.get('outfit_images') or '[]')
                row['outfit_images'] = json.dumps([
                    add_file(source) if (source := local_asset(value, root)) else value
                    for value in outfits], ensure_ascii=False)
            if name == 'knowledge_document':
                source = local_asset(row['file_path'], root)
                if source is None:
                    raise ValueError('Knowledge documents must be local files')
                row['content_hash'] = hashlib.sha256(source.read_bytes()).hexdigest()
                row['status'], row['chunk_count'] = 'pending', 0
    for relative, source in sorted(sources.items()):
        payload['files'][relative] = hashlib.sha256(source.read_bytes()).hexdigest()
    manifest = json.dumps(payload, ensure_ascii=False, indent=2,
                          default=lambda value: value.isoformat() if isinstance(value, (date, datetime)) else str(value))
    # Check exact local secret values as well as commonly recognizable token formats.
    secrets = [value for key, value in os.environ.items()
               if re.search(r'SECRET|PASSWORD|API_KEY|TOKEN.*KEY', key, re.I) and len(value) >= 12]
    text_blobs = [manifest]
    for source in sources.values():
        if source.suffix.lower() in ('.json', '.md', '.txt', '.gltf', '.svg'):
            text_blobs.append(source.read_text(encoding='utf-8'))
    for content in text_blobs:
        if any(secret in content for secret in secrets) or re.search(
                r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|\b(?:sk-[A-Za-z0-9_-]{24,}|gh[pousr]_[A-Za-z0-9]{30,})\b', content):
            raise ValueError('Potential secret detected; public export refused')
    output.mkdir(parents=True)
    for relative, source in sources.items():
        destination = output / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    (output / 'resources.json').write_text(manifest + '\n', encoding='utf-8')
    counts = {name: len(rows) for name, rows in tables.items()}
    (output / 'README.md').write_text(
        '# 本机颐和园资源包\n\n'
        f"包含 {counts['scenic_spot_info']} 个景点、{counts['tour_route']} 条路线、"
        f"{counts['digital_guide_info']} 个数字人配置、{counts['knowledge_document']} 份知识文档，"
        f"{len(sources)} 个素材文件。\n\n"
        '此包是本机未删除内容的快照，包括已下架的数字人。所有数字人导入后默认下架；'
        '星云角色需绑定接收方自己的应用。\n\n'
        '不含用户账号、密码、游客会话、星云应用绑定、平台密钥或数据库备份。'
        '知识文档需在接收方重新建立索引。原始景点 ID 是导入映射依据，导入后的 ID 可能变化。\n\n'
        '解压后先按项目说明配置 .env、初始化数据库和管理员，再执行：\n\n'
        '```powershell\npython scripts/import_resource_pack.py resources/local-resources\n```\n\n'
        '已有同名数据库记录会保留；已有且内容不同的素材会拒绝覆盖。'
        '要复现这份快照，建议使用空数据库。来源引用见景点描述及知识文档。\n', encoding='utf-8')
    return counts


def zip_pack(folder, destination):
    if destination.exists():
        raise ValueError('Archive already exists; refusing overwrite')
    with zipfile.ZipFile(destination, 'x', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(folder.rglob('*')):
            if path.is_file():
                archive.write(path, (Path(folder.name) / path.relative_to(folder)).as_posix())
    with zipfile.ZipFile(destination) as archive:
        if archive.testzip() is not None:
            raise ValueError('Archive integrity check failed')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--zip', dest='archive', type=Path)
    args = parser.parse_args()
    load_dotenv(ROOT / '.env', override=True)
    engine = create_engine(URL.create('postgresql+psycopg', username=os.getenv('POSTGRES_USER', 'postgres'),
        password=os.environ['POSTGRES_PASSWORD'], host=os.getenv('POSTGRES_SERVER', '127.0.0.1'),
        port=int(os.getenv('POSTGRES_PORT', '15432')), database=os.getenv('POSTGRES_DB', 'streamer_sales_db')))
    counts = export_pack(ROOT, engine, args.output)
    if args.archive:
        zip_pack(args.output, args.archive)
    print(json.dumps(counts, ensure_ascii=False))


if __name__ == '__main__':
    main()
