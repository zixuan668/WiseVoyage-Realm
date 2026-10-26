"""Verify older public rows against freshly reflected tables with NOT NULL fields."""
import hashlib
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import MetaData, Table, select
from sqlmodel import SQLModel, Session, create_engine
from server.base.models.user_model import UserInfo

spec = importlib.util.spec_from_file_location('resource_import', Path(__file__).parents[1] / 'import_resource_pack.py')
importer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(importer)


class ResourceImportTests(unittest.TestCase):
    def test_missing_defaults_and_repeat_import_preserve_configured_guide(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            pack = root / 'pack'
            pack.mkdir()
            payload = {'tables': {name: [] for name in importer.TABLES}, 'files': {}}
            payload['tables']['digital_guide_info'] = [{'guide_id': 51, 'name': 'legacy guide'}]
            (pack / 'resources.json').write_text(json.dumps(payload), encoding='utf-8')
            engine = create_engine('sqlite://')
            SQLModel.metadata.create_all(engine)
            with Session(engine) as db:
                db.add(UserInfo(username='admin', hashed_password='unused'))
                db.commit()
            with patch.object(importer, 'ROOT', root), patch.object(importer, 'create_engine', return_value=engine), \
                 patch.object(importer, 'load_dotenv'), patch.dict(os.environ, POSTGRES_PASSWORD='test', ADMIN_USERNAME='admin'), \
                 patch('sys.argv', ['import_resource_pack.py', str(pack)]):
                importer.main()
                guide = Table('digital_guide_info', MetaData(), autoload_with=engine)
                with engine.begin() as db:
                    row = db.execute(select(guide)).mappings().one()
                    self.assertEqual(row['language'], 'zh')
                    self.assertEqual(row['name_en'], '')
                    self.assertEqual(row['character_en'], '')
                    self.assertEqual(row['model3d_path'], '')
                    self.assertEqual(row['live2d_model_path'], '')
                    self.assertFalse(row['is_enabled'])
                    db.execute(guide.update().values(language='en', is_enabled=True))
                importer.main()
                with engine.connect() as db:
                    row = db.execute(select(guide)).mappings().one()
                    self.assertEqual(row['language'], 'en')
                    self.assertTrue(row['is_enabled'])
            engine.dispose()

    def test_conflicting_asset_still_fails_before_database_access(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            pack = root / 'pack'
            (pack / 'static').mkdir(parents=True)
            (root / 'static').mkdir()
            (pack / 'static/a.md').write_bytes(b'new')
            (root / 'static/a.md').write_bytes(b'original')
            payload = {'tables': {name: [] for name in importer.TABLES},
                       'files': {'static/a.md': hashlib.sha256(b'new').hexdigest()}}
            (pack / 'resources.json').write_text(json.dumps(payload), encoding='utf-8')
            with patch.object(importer, 'ROOT', root), patch.object(importer, 'create_engine') as connect, \
                 patch('sys.argv', ['import_resource_pack.py', str(pack)]):
                with self.assertRaisesRegex(ValueError, 'refusing overwrite'):
                    importer.main()
                connect.assert_not_called()
                self.assertEqual((root / 'static/a.md').read_bytes(), b'original')


if __name__ == '__main__':
    unittest.main()
