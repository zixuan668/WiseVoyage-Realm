import unittest
import tempfile
from pathlib import Path
from types import SimpleNamespace
from server.base.modules.scenic_narration import narration_text, narration_revision


class NarrationTests(unittest.TestCase):
    def test_complete_script_and_empty_fields(self):
        spot = SimpleNamespace(spot_name='长廊', description='介绍', history_detail='历史',
            tour_tips='提醒', photo_tips='拍照', best_season='春秋', service_facilities='设施')
        text = narration_text(spot)
        for value in ['长廊', '介绍', '历史', '提醒', '拍照', '春秋', '设施']:
            self.assertIn(value, text)
        self.assertEqual(narration_text(SimpleNamespace(spot_name='空景点')), '')

    def test_version_tracks_content_and_voice(self):
        self.assertEqual(narration_revision('内容', '角色'), narration_revision('内容', '角色'))
        self.assertNotEqual(narration_revision('内容', '角色'), narration_revision('新内容', '角色'))
        self.assertNotEqual(narration_revision('内容', '角色'), narration_revision('内容', '新角色'))

    def test_missing_and_escaped_files_are_rejected(self):
        from server.base.modules.scenic_narration import recording_file
        with tempfile.TemporaryDirectory() as root:
            self.assertIsNone(recording_file(root, SimpleNamespace(file_name='missing.webm')))
            with tempfile.NamedTemporaryFile() as outside:
                self.assertIsNone(recording_file(root, SimpleNamespace(file_name=outside.name)))


class AudioApiTests(unittest.IsolatedAsyncioTestCase):
    async def test_recording_and_stale_deleted_missing_cases(self):
        from dotenv import load_dotenv
        load_dotenv(Path(__file__).resolve().parents[2] / '.env')
        from sqlmodel import Session, create_engine
        from sqlalchemy.pool import StaticPool
        from fastapi import FastAPI
        from unittest.mock import patch
        import httpx
        from server.base.routers import tour_experience as api
        from server.base.models.scenic_audio import ScenicAudio
        from server.base.models.tour_models import ScenicSpotInfo
        from server.base.models.xingyun import XingyunGuideBinding
        from server.base.modules.scenic_narration import voice_identity
        engine = create_engine('sqlite://', connect_args={'check_same_thread':False}, poolclass=StaticPool)
        for model in [ScenicSpotInfo, XingyunGuideBinding, ScenicAudio]:
            model.__table__.create(engine)
        spot = ScenicSpotInfo(spot_id=1, spot_name='长廊', description='完整介绍', best_season='秋季')
        binding = XingyunGuideBinding(guide_id=1, app_id='test', secret_encrypted='not-a-secret')
        with Session(engine) as db:
            db.add(spot); db.add(binding); db.commit()
        app = FastAPI(); app.include_router(api.router)
        with tempfile.TemporaryDirectory() as root, patch.object(api, 'DB_ENGINE', engine), patch('server.web_configs.WEB_CONFIGS.SERVER_FILE_ROOT', root):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
                self.assertEqual((await client.get('/tour-experience/scenic-audio/1')).status_code,409)
                folder = Path(root)/'tour_files/scenic-audio'; folder.mkdir(parents=True)
                (folder/'test.webm').write_bytes(b'\x1aE\xdf\xa3'+b'x'*200)
                with Session(engine) as db:
                    spot=db.get(ScenicSpotInfo,1); binding=db.get(XingyunGuideBinding,1)
                    db.add(ScenicAudio(spot_id=1,guide_id=1,revision=narration_revision(narration_text(spot),voice_identity(binding)),
                        script=narration_text(spot),file_name='test.webm',duration=10)); db.commit()
                res=await client.get('/tour-experience/scenic-audio/1')
                self.assertEqual(res.status_code,200)
                self.assertEqual(res.json()['source'],'xingyun-recording')
                self.assertEqual((await client.get(res.json()['url'])).status_code,200)
                with Session(engine) as db:
                    spot=db.get(ScenicSpotInfo,1);spot.best_season='春季';db.add(spot);db.commit()
                self.assertEqual((await client.get('/tour-experience/scenic-audio/1/file')).status_code,409)
                with Session(engine) as db:
                    spot=db.get(ScenicSpotInfo,1);spot.delete=True;db.add(spot);db.commit()
                self.assertEqual((await client.get('/tour-experience/scenic-audio/1')).status_code,404)
        engine.dispose()
