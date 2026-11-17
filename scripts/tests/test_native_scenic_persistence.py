"""Execute production draft handlers against an isolated in-memory database."""
import ast,json,unittest
from pathlib import Path
from typing import Literal
from fastapi import Request,Response,HTTPException
from pydantic import BaseModel,Field
from sqlmodel import SQLModel,Session,select,create_engine,Field as Column
from sqlalchemy import event
from sqlalchemy.pool import StaticPool

class ScenicSpotInfo(SQLModel,table=True):
    spot_id:int=Column(primary_key=True)
    spot_name:str
    delete:bool=False

names={'ScenicDraftStop','ScenicDraftSettings','DraftSettingsInput','scenic_draft_owner','scenic_selection','select_stop','remove_stop','draft_settings_data','get_draft_settings','save_draft_settings'}
tree=ast.parse(Path('server/base/routers/tour_experience.py').read_text(encoding='utf-8'))
nodes=[node for node in tree.body if isinstance(node,(ast.FunctionDef,ast.ClassDef)) and node.name in names]
for node in nodes:
    if isinstance(node,ast.FunctionDef):node.decorator_list=[]
scope=dict(globals(),get_current_user_info=lambda token:int(token),load_spots=lambda db,ids:None)
exec(compile(ast.Module(body=nodes,type_ignores=[]),'production-draft-handlers','exec'),scope)

class NativeScenicPersistenceTests(unittest.TestCase):
    def test_database_drafts_are_persisted_and_isolated_by_verified_account(self):
        engine=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
        @event.listens_for(engine,'connect')
        def register_functions(connection,_):
            connection.create_function('hashtext',1,lambda value:1)
            connection.create_function('pg_advisory_xact_lock',1,lambda value:None)
        scope['DB_ENGINE']=engine
        for name in ('ScenicSpotInfo','ScenicDraftStop','ScenicDraftSettings'):scope[name].__table__.create(engine)
        with Session(engine) as db:db.add(ScenicSpotInfo(spot_id=501,spot_name='测试景点'));db.commit()
        def request(account):return Request({'type':'http','headers':[(b'authorization',f'Bearer {account}'.encode())]})
        first,second=request(17),request(18)
        scope['select_stop'](501,first)
        self.assertEqual(scope['scenic_selection'](first,Response())[0]['id'],501)
        self.assertEqual(scope['scenic_selection'](second,Response()),[])
        scope['save_draft_settings'](scope['DraftSettingsInput'](spot_ids=[501],elderly=True,start_area='east'),first)
        self.assertTrue(scope['get_draft_settings'](first)['elderly'])
        self.assertEqual(scope['get_draft_settings'](first)['start_area'],'east')
        self.assertFalse(scope['get_draft_settings'](second)['elderly'])
        scope['remove_stop'](501,second)
        self.assertEqual(len(scope['scenic_selection'](first,Response())),1)
        scope['remove_stop'](501,first)
        self.assertEqual(scope['scenic_selection'](first,Response()),[])
        engine.dispose()
if __name__=='__main__':unittest.main()
