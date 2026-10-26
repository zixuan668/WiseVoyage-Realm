import hashlib
import importlib.util
import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import Boolean, Column, Integer, MetaData, String, Table, create_engine

spec = importlib.util.spec_from_file_location('resource_export', Path(__file__).parents[1] / 'export_resource_pack.py')
exporter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(exporter)


class ResourceExportTests(unittest.TestCase):
    def test_normalize_local_url_and_reject_encoded_escape(self):
        root = Path(tempfile.gettempdir()).resolve() / 'resource-path-test'
        self.assertEqual(exporter.local_asset('http://localhost:8000/api/v1/files\\images\\a.png', root),
                         root / 'static/images/a.png')
        self.assertIsNone(exporter.local_asset('https://example.org/image.png', root))
        for value in ('../.env', '/api/v1/files/%2e%2e/.env'):
            with self.assertRaises(ValueError):
                exporter.local_asset(value, root)

    def fixture(self, root):
        engine = create_engine('sqlite://')
        metadata = MetaData()
        tables = {
            'scenic_spot_info': Table('scenic_spot_info', metadata, Column('spot_id', Integer, primary_key=True),
                Column('spot_name', String), Column('delete', Boolean), Column('user_id', Integer), Column('api_key', String)),
            'tour_route': Table('tour_route', metadata, Column('route_id', Integer, primary_key=True), Column('name', String), Column('delete', Boolean)),
            'digital_guide_info': Table('digital_guide_info', metadata, Column('guide_id', Integer, primary_key=True),
                Column('name', String), Column('delete', Boolean), Column('is_enabled', Boolean)),
            'knowledge_document': Table('knowledge_document', metadata, Column('doc_id', Integer, primary_key=True),
                Column('title', String), Column('file_path', String), Column('content_hash', String)),
            'tour_route_spot': Table('tour_route_spot', metadata, Column('id', Integer, primary_key=True), Column('route_id', Integer), Column('spot_id', Integer)),
        }
        metadata.create_all(engine)
        with engine.begin() as db:
            db.execute(tables['scenic_spot_info'].insert(), [
                dict(spot_id=1, spot_name='保留景点', delete=False, user_id=9, api_key='never-export-this-value'),
                dict(spot_id=2, spot_name='已删除', delete=True, user_id=9, api_key='never-export-this-value')])
            db.execute(tables['tour_route'].insert(), dict(route_id=1, name='路线', delete=False))
            db.execute(tables['tour_route_spot'].insert(), [dict(id=1, route_id=1, spot_id=1), dict(id=2, route_id=1, spot_id=2)])
            db.execute(tables['digital_guide_info'].insert(), dict(guide_id=1, name='角色', delete=False,
                is_enabled=True))
            db.execute(tables['knowledge_document'].insert(), dict(doc_id=1, title='知识', file_path='knowledge/a.md', content_hash='old'))
        for name, content in [('knowledge/a.md', b'knowledge')]:
            p = root / 'static' / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(content)
        return engine

    def test_public_snapshot_filters_secrets_deleted_rows_and_dangling_links(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            counts = exporter.export_pack(root, self.fixture(root), root / 'pack')
            raw = (root / 'pack/resources.json').read_text(encoding='utf-8')
            data = json.loads(raw)
            self.assertEqual(counts['scenic_spot_info'], 1)
            self.assertEqual(counts['tour_route_spot'], 1)
            self.assertNotIn('api_key', raw)
            self.assertNotIn('never-export-this-value', raw)
            self.assertNotIn('user_id', raw)
            self.assertFalse(data['tables']['digital_guide_info'][0]['is_enabled'])
            document = data['tables']['knowledge_document'][0]
            self.assertEqual(document['status'], 'pending')
            self.assertEqual(document['content_hash'], hashlib.sha256(b'knowledge').hexdigest())
            archive = root / 'pack.zip'
            exporter.zip_pack(root / 'pack', archive)
            with zipfile.ZipFile(archive) as zipped:
                self.assertIsNone(zipped.testzip())
                for path, digest in data['files'].items():
                    self.assertEqual(hashlib.sha256(zipped.read('pack/' + path)).hexdigest(), digest)

    def test_secret_in_document_stops_export_before_writing(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            engine = self.fixture(root)
            (root / 'static/knowledge/a.md').write_text('example-secret-value-123456', encoding='utf-8')
            with patch.dict(os.environ, {'EXAMPLE_API_KEY': 'example-secret-value-123456'}):
                with self.assertRaisesRegex(ValueError, 'secret'):
                    exporter.export_pack(root, engine, root / 'pack')
            self.assertFalse((root / 'pack').exists())

    def test_missing_asset_and_existing_output_are_not_silently_ignored(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            engine = self.fixture(root)
            (root / 'static/knowledge/a.md').unlink()
            with self.assertRaises(FileNotFoundError):
                exporter.export_pack(root, engine, root / 'pack')
            (root / 'pack').mkdir()
            with self.assertRaisesRegex(ValueError, 'already exists'):
                exporter.export_pack(root, engine, root / 'pack')


if __name__ == '__main__':
    unittest.main()
