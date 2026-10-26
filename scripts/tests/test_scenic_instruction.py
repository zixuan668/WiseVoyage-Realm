import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from server.base.routers import scenic_spots as api


class ScenicInstructionTests(unittest.IsolatedAsyncioTestCase):
    async def test_read_owned_document_as_utf8(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'tour').mkdir()
            (root / 'tour/guide.md').write_text('# 仁寿殿\n景点游览说明', encoding='utf-8-sig')
            rows = [SimpleNamespace(instruction=api.API_CONFIG.REQUEST_FILES_URL + '/tour/guide.md')]
            with patch.object(api.WEB_CONFIGS, 'SERVER_FILE_ROOT', directory), patch.object(
                api, 'get_db_scenic_spot_info', new_callable=AsyncMock, return_value=(rows, 1)
            ) as query:
                result = await api.get_spot_instruction(3, 7)
            self.assertEqual(result['data'], '# 仁寿殿\n景点游览说明')
            query.assert_awaited_once_with(user_id=7, spot_id=3)

    async def test_missing_or_other_owners_spot_is_not_read(self):
        with patch.object(api, 'get_db_scenic_spot_info', new_callable=AsyncMock, return_value=([], 0)):
            with self.assertRaises(HTTPException) as error:
                await api.get_spot_instruction(3, 8)
        self.assertEqual(error.exception.status_code, 404)

    async def test_database_path_cannot_escape_static_root(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'static').mkdir()
            (root / 'private.md').write_text('private', encoding='utf-8')
            rows = [SimpleNamespace(instruction=api.API_CONFIG.REQUEST_FILES_URL + '/%2e%2e/private.md')]
            with patch.object(api.WEB_CONFIGS, 'SERVER_FILE_ROOT', str(root / 'static')), patch.object(
                api, 'get_db_scenic_spot_info', new_callable=AsyncMock, return_value=(rows, 1)
            ):
                with self.assertRaises(HTTPException) as error:
                    await api.get_spot_instruction(3, 7)
            self.assertEqual(error.exception.status_code, 404)
