"""Opt-in DB/API acceptance: creates and ends one labelled verification tour.

Run against the local demo DB only. Provider/TTS calls are mocked in the in-process
route checks; --http additionally checks one real HTTP answer with normal TTS.
No keys are printed, and no existing visitor tours or coordinates are modified.
"""
import asyncio
import json
import sys
from unittest.mock import AsyncMock, patch
import requests
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv
load_dotenv(ROOT / '.env')
from sqlmodel import Session, select
from server.base.database.init_db import DB_ENGINE
from fastapi import BackgroundTasks
from server.base.models.tour_models import ScenicSpotInfo, TourSessionInfo
from server.base.routers.tour_chat import tour_chat
from server.base.models.tour_models import TourChatItem
from server.base.database.tour_session_db import get_session_live_info, end_tour_session, get_dialogue_context
from server.base.modules.rag.rag_worker import load_tour_rag_model
from loguru import logger
logger.remove()
logger.add(sys.stderr,level='WARNING')

BASE='http://127.0.0.1:8000/tour-session'


async def main():
    with Session(DB_ENGINE) as db:
        spots={s.spot_name:s.model_dump() for s in db.exec(select(ScenicSpotInfo).where(ScenicSpotInfo.delete==False)).all()}
    guide=requests.get(BASE+'/guides',timeout=10).json()['data']['guide_list'][0]['guide_id']
    ids=[spots[n]['spot_id'] for n in ['长廊','昆明湖','十七孔桥']]
    created=requests.post(BASE+'/visitor-create',params=dict(name='知识问答验收',guide_id=guide,spot_ids=json.dumps(ids)),timeout=15).json()
    assert created['success'],created.get('message')
    sid=created['data']['session_id']
    print('Verification session:',sid)
    await load_tour_rag_model(1)
    try:
        async def chat(question, name='长廊'):
            result=await tour_chat(TourChatItem(sessionId=sid,message=question,currentSpotId=spots[name]['spot_id'],nextSpotId=spots['昆明湖']['spot_id']),BackgroundTasks())
            assert result['success'],result
            return result['data']
        with patch('server.base.modules.edge_tts_client.synthesize_speech',new=AsyncMock(return_value='')), \
             patch('server.base.routers.tour_chat._llm_is_configured',return_value=False):
            photo=await chat('最佳拍照点在哪里？')
            assert photo['aiMeta']['intents']==['photography'] and '柱列' in photo['message']
            facilities=await chat('附近哪里有厕所？')
            assert facilities['aiMeta']['intents']==['facilities'] and '核实' in facilities['message']
            nxt=await chat('下一站去哪儿？')
            assert nxt['aiMeta']['intents']==['next'] and '昆明湖' in nxt['message']
            history=await chat('介绍一下长廊的历史')
            detailed=await chat('再详细讲讲')
            assert detailed['aiMeta']['followUp'] and len(detailed['message'])>len(history['message'])
            assert len(detailed['spokenText'])<=460
            short=await chat('一句话说重点')
            assert len(short['message'])<=160
            named=await chat('石舫真的能开走吗？')
            assert named['aiMeta']['spotContext']=='石舫' and '不能' in named['message']
            named_follow=await chat('那它为什么叫清晏舫？')
            assert named_follow['aiMeta']['spotContext']=='石舫' and '安宁' in named_follow['message']
            changed=await chat('那为什么呢？','昆明湖')
            assert changed['aiMeta']['intents']==['clarify']
            mixed=await chat('讲讲历史，另外哪里拍照好？')
            assert {'history','photography'}.issubset(mixed['aiMeta']['intents'])
            comparison=await chat('长廊和佛香阁哪个更适合轮椅？')
            assert '长廊：' in comparison['message'] and '佛香阁：' in comparison['message']
        saved=await get_session_live_info(sid)
        assert saved['conversation'][-1]['aiMeta']['sources']
        assert get_dialogue_context(sid)['active_spot_id']==spots['长廊']['spot_id']
        if '--http' in sys.argv:
            reply=requests.put(BASE+'/chat',json=dict(sessionId=sid,message='长廊有多长？',currentSpotId=spots['长廊']['spot_id'],avatarMode='audio'),timeout=90).json()
            assert reply['success'] and '728' in reply['data']['message']
            print('Real HTTP answer:',reply['data']['message'])
            print('Answer mode:',reply['data']['aiMeta']['answerMode'])
            print('RAG applied:',reply['data']['aiMeta']['ragApplied'])
            print('Speech available:',bool(reply['data'].get('ttsAudioUrl')))
        print('PASS: 11 database-backed dialogue cases, persisted provenance, scoped memory')
    finally:
        await end_tour_session(sid)


if __name__=='__main__': asyncio.run(main())
