"""Update only knowledge fields of existing POIs; preserve coordinates and tours.

Backs up affected rows to ignored work_dirs before writing. Idempotent: no new
POIs, route changes, account changes, or deleted document/spot restoration.
"""
import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)
from dotenv import load_dotenv
load_dotenv(ROOT / '.env')
from sqlmodel import Session, select
from server.base.database.init_db import DB_ENGINE
from server.base.models.tour_models import ScenicSpotInfo, KnowledgeDocument


def main():
    book = json.loads((ROOT/"data/summer_palace_knowledge.json").read_text(encoding="utf-8"))
    changes = []
    with Session(DB_ENGINE) as db:
        spots = db.exec(select(ScenicSpotInfo).where(ScenicSpotInfo.delete == False)).all()
        for spot in spots:
            if spot.spot_name not in book["spots"] or spot.city not in ("北京", "北京市"):
                continue
            if not 39.97 < spot.latitude < 40.02 or not 116.24 < spot.longitude < 116.30:
                continue
            changes.append(spot.model_dump(mode="json"))
        backup = ROOT/"work_dirs"/f"knowledge-backup-{datetime.now():%Y%m%d-%H%M%S-%f}.json"
        backup.parent.mkdir(exist_ok=True)
        backup.write_text(json.dumps(changes,ensure_ascii=False,indent=2),encoding="utf-8")
        ids = {item["spot_id"] for item in changes}
        for spot in spots:
            if spot.spot_id not in ids: continue
            d=book["spots"][spot.spot_name]
            spot.description=d["overview"]
            spot.history_detail=d["history"]+"\n"+d["architecture"]+"\n"+d["misconceptions"]
            spot.photo_tips=d["photography"]
            spot.tour_tips="\n".join(d["highlights"])+"\n"+d["family"]+"\n"+d["accessibility"]
            spot.service_facilities=d["facilities"]
            spot.best_season=d["season"]
            spot.instruction=d["document_path"]
            db.add(spot)
            doc=db.exec(select(KnowledgeDocument).where(KnowledgeDocument.file_path==d["document_path"],KnowledgeDocument.user_id==spot.user_id)).first()
            if doc is None:
                doc=KnowledgeDocument(title=f"颐和园·{spot.spot_name}详细知识档案",file_path=d["document_path"],user_id=spot.user_id)
            doc.file_type="md"
            doc.content_hash=hashlib.sha256((ROOT/"static"/d["document_path"]).read_bytes()).hexdigest()
            doc.chunk_count=16
            doc.status="completed"
            db.add(doc)
        db.commit()
    print(f"Updated {len(changes)} existing spots and their knowledge records. Backup: {backup.name}")


if __name__=="__main__": main()
