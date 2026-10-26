"""Deterministic visual attachments. Never let a model invent image URLs or dates."""
import json
import re
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

from .tour_knowledge import dossier_for


@lru_cache(maxsize=1)
def visual_catalog():
    path = Path(__file__).resolve().parents[3] / 'data/tour_visual_catalog.json'
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}


def safe_image(value):
    value = str(value or '').replace('\\', '/')
    if not value or '..' in value or value.startswith('//'):
        return ''
    parsed = urlparse(value)
    # The uploader returns a full API URL; render its local path so a stale
    # localhost host/port never leaks into the visitor's browser.
    if parsed.scheme in ('http','https') and parsed.path.startswith('/api/v1/files/'):
        return parsed.path
    if parsed.scheme:
        return value if parsed.scheme == 'https' and parsed.hostname in {
            'www.summerpalace.net.cn', 'r1.visitbeijing.com.cn', 'vbj-rscn.huanqiucdn.cn'} else ''
    if value.startswith('/api/v1/files/'):
        return value
    if not parsed.netloc and not value.startswith('/'):
        return '/api/v1/files/' + value
    return ''


def build_visual_context(spot, intents, answer, language='zh', historical=None):
    if not spot or not set(intents) & {'overview', 'history', 'architecture', 'highlights', 'photography'}:
        return None
    # Unknown content and unrelated namesakes must not inherit park imagery.
    dossier = dossier_for(spot)
    catalog = visual_catalog().get(spot.get('spot_name'), {}) if dossier else {}
    en = language == 'en'
    image = safe_image(spot.get('image_path'))
    pictures = ([dict(url=image, label='管理员配置图片' if not en else 'Configured attraction image', source='')]
                if image else catalog.get('images', []))
    pictures = [dict(url=safe_image(p.get('url')), label=p.get('en' if en else 'zh') or p.get('label', ''),
                     source=p.get('source', '')) for p in pictures if safe_image(p.get('url'))][:3]
    timeline = []
    for record in catalog.get('timeline', []):
        # Show chronology only when this answer actually discusses its date.
        if str(record['year']) in answer and 'history' in intents:
            timeline.append(dict(year=record['year'], text=record['en' if en else 'zh'], source=record['source']))
    if historical and historical.get('persona', {}).get('timeline'):
        timeline = historical['persona']['timeline'][:5]
    if not pictures and not timeline:
        return None
    return dict(spot_id=spot.get('spot_id'), spot_name=spot.get('spot_name'), images=pictures,
                timeline=timeline, linked_topics=intents,
                note='Images are reference material, not a live view.' if en else '图片用于辅助理解，不代表现场实时画面。')
