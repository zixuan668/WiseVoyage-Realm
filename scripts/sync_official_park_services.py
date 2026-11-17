"""Import the official park-level facility catalog and update only matching knowledge sections."""
import asyncio
import hashlib
import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from sqlmodel import Session, select

ROOT=Path(__file__).resolve().parents[1]
load_dotenv(ROOT/'.env')
from server.base.database.init_db import DB_ENGINE
from server.base.models.tour_models import ScenicSpotInfo, KnowledgeDocument
from server.base.routers.tour_experience import ScenicParkServices
from server.base.modules.knowledge_review import publish_submitted_documents
from server.base.modules.rag import rag_worker


async def main():
    services=json.loads((ROOT/'data/summer_palace_services.json').read_text(encoding='utf8'))
    labels='、'.join(item['label'] for item in services['categories'])
    text='颐和园全园设施包括'+labels+'。具体点位见官网导览图，当前景点周边位置及当日开放情况以园内指引为准。'
    book_path=ROOT/'data/summer_palace_knowledge.json'
    book=json.loads(book_path.read_text(encoding='utf8'))
    book['sources']['guide_map']=['颐和园官网导览地图',services['source_url']]
    backup=ROOT/'work_dirs'/('official-services-'+datetime.now().strftime('%Y%m%d-%H%M%S'))
    backup.mkdir(parents=True,exist_ok=True)
    shutil.copy2(book_path,backup/book_path.name)
    doc_path='knowledge_base/official_park_services.md'
    source_line='- [颐和园官网导览地图]('+services['source_url']+')'
    content='# 颐和园全园服务设施目录\n\n核对日期 '+services['checked_at']+'\n\n'
    content+='## 使用范围\n'+text+'\n\n'
    for item in services['categories']:
        content+='## '+item['label']+'\n官网导览图提供该类别的全园点位。\n\n'
    content+='## 无障碍服务\n园内官方无障碍环线分为平缓环线和含山体道路的环线。不能仅根据类别名称推定每段坡度或现场通行条件。\n\n'
    content+='## 地图坐标说明\n本目录保留官网图片像素点位，不是GPS坐标，不能直接计算最近距离或用作导航。\n\n'
    content+='## 资料来源\n'+source_line+'\n- [官网轮椅服务与两条无障碍环线](https://summerpalace.net.cn/single/detail/508.html)\n'
    target=ROOT/'static'/doc_path
    target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists():shutil.copy2(target,backup/'official_park_services.md')
    target.write_text(content,encoding='utf8')
    ScenicParkServices.__table__.create(DB_ENGINE,checkfirst=True)
    changed=[]
    with Session(DB_ENGINE) as db:
        spots=db.exec(select(ScenicSpotInfo).where(ScenicSpotInfo.delete==False)).all()
        campus=next((s for s in spots if s.spot_name in ('致远楼','智远楼')),None)
        test_point={'name':campus.spot_name,'id':campus.spot_id,'exists':True,'trigger_radius':campus.trigger_radius} if campus else {'exists':False}
        formal=[s for s in spots if s.spot_name in book['spots'] and s.city in ('北京','北京市') and 39.97<s.latitude<40.02 and 116.24<s.longitude<116.30]
        backup_rows=[s.model_dump(mode='json') for s in formal]
        (backup/'spots.json').write_text(json.dumps(backup_rows,ensure_ascii=False,indent=2),encoding='utf8')
        for spot in formal:
            record=book['spots'][spot.spot_name]
            record['overview']=spot.description
            record['facilities']=text
            if 'guide_map' not in record.get('source_ids',[]):record.setdefault('source_ids',[]).append('guide_map')
            if not any(source.get('id')=='guide_map' for source in record['sources']):
                record['sources'].append({'id':'guide_map','title':'颐和园官网导览地图','url':services['source_url']})
            for qa in record.get('qa',[]):
                if qa.get('topic')=='facilities':
                    qa['answer']=text;qa['source_ids']=['guide_map']
            path=ROOT/'static'/record['document_path']
            old=path.read_text(encoding='utf8')
            shutil.copy2(path,backup/path.name)
            new=re.sub(r'(## 景点概览\n).*?(?=\n<!-- spot:|\n## |\Z)',lambda m:m[1]+spot.description+'\n',old,flags=re.S)
            new=re.sub(r'(## 服务设施\n).*?(?=\n<!-- spot:|\n## |\Z)',lambda m:m[1]+text+'\n',new,flags=re.S)
            # Update only the answer to facilities questions in the FAQ section.
            new=new.replace(old.split('## 服务设施\n')[1].split('\n<!-- spot:')[0].strip(),text) if '## 服务设施\n' in old else new
            if source_line not in new:new+='\n'+source_line+'\n'
            path.write_text(new,encoding='utf8')
            spot.service_facilities=text
            db.add(spot)
            doc=db.exec(select(KnowledgeDocument).where(KnowledgeDocument.file_path==record['document_path'],KnowledgeDocument.user_id==spot.user_id)).first()
            if doc:
                doc.content_hash=hashlib.sha256(path.read_bytes()).hexdigest()
                db.add(doc)
            changed.append({'id':spot.spot_id,'name':spot.spot_name,'knowledge_document':record['document_path'],'coordinate_configured':bool(spot.latitude and spot.longitude)})
        row=db.get(ScenicParkServices,'summer-palace') or ScenicParkServices(park_id='summer-palace',payload='')
        row.payload=json.dumps(services,ensure_ascii=False)
        db.add(row)
        owner=formal[0].user_id
        doc=db.exec(select(KnowledgeDocument).where(KnowledgeDocument.file_path==doc_path,KnowledgeDocument.user_id==owner)).first()
        digest=hashlib.sha256(target.read_bytes()).hexdigest()
        if doc is None:
            doc=KnowledgeDocument(title='颐和园官网服务设施目录',file_path=doc_path,file_type='md',user_id=owner,status='pending')
        elif doc.content_hash!=digest:
            doc.status='pending'
        db.add(doc);db.commit();db.refresh(doc)
        pending_id=doc.doc_id if doc.status=='pending' else None
    book_path.write_text(json.dumps(book,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    if pending_id:
        await publish_submitted_documents(DB_ENGINE,owner,[pending_id])
    prepared=await rag_worker._load_lightweight_tour_retriever(owner)
    counts=rag_worker.document_chunk_counts(prepared)
    with Session(DB_ENGINE) as db:
        for doc in db.exec(select(KnowledgeDocument).where(KnowledgeDocument.user_id==owner,KnowledgeDocument.status=='completed')).all():
            doc.chunk_count=counts.get(Path(doc.file_path).name,0);db.add(doc)
        db.commit()
    report={'checked_at':services['checked_at'],'formal_spots':changed,'facility_categories':len(services['categories']),
        'knowledge_index_version':prepared.index_version,'backup':str(backup),
        'test_point':test_point,
        'note':'未将官网像素坐标转换为GPS，未将全园设施归属到单个景点。'}
    (ROOT/'outputs/scenic-knowledge-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print('Updated',len(changed),'formal scenic dossiers;',len(services['categories']),'official facility categories; index',prepared.index_version)


if __name__=='__main__':
    asyncio.run(main())
