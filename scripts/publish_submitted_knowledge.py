"""Accept legacy administrator submissions and back up their previous database state."""
import argparse
import asyncio
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
from server.base.models.tour_models import KnowledgeDocument, KnowledgeReview
from server.base.modules.knowledge_review import publish_submitted_documents


async def main(user_id):
    with Session(DB_ENGINE) as db:
        docs = db.exec(select(KnowledgeDocument).where(KnowledgeDocument.user_id == user_id)).all()
        reviews = db.exec(select(KnowledgeReview).where(KnowledgeReview.reviewer_id == user_id)).all()
        # Do not republish documents deliberately withdrawn or rejected in the old workflow.
        reviewed_ids = {review.doc_id for review in reviews}
        ids = [doc.doc_id for doc in docs if doc.status == 'pending' and doc.doc_id not in reviewed_ids]
        if not ids:
            print(json.dumps({'published': 0, 'message': 'No legacy submissions need publication'}))
            return
        backup = ROOT / 'work_dirs' / ('knowledge-autopublish-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.json')
        backup.parent.mkdir(exist_ok=True, parents=True)
        backup.write_text(json.dumps({
            'documents': [doc.model_dump(mode='json') for doc in docs],
            'reviews': [review.model_dump(mode='json') for review in reviews],
        }, ensure_ascii=False, indent=2), encoding='utf-8')
    result = await publish_submitted_documents(DB_ENGINE, user_id, ids)
    print(json.dumps({'published': len(result['documents']),
                      'indexed_chunks': sum(doc['chunk_count'] for doc in result['documents']),
                      'index_version': result['index_version'], 'backup': str(backup)}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--user-id', type=int, default=1)
    asyncio.run(main(parser.parse_args().user_id))
