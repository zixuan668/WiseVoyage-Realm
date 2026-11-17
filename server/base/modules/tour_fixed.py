"""固定问答：给演示里必须稳定输出的问题准备逐字回答，命中后不再走模型。"""
import json
from pathlib import Path

_PATH = Path(__file__).resolve().parents[3] / 'data' / 'tour_fixed_answers.json'
_CACHE = {'mtime': None, 'items': []}


def _normalize(text):
    return ''.join(ch for ch in str(text or '') if ch not in ' \t\r\n，,。.？?！!、；;：:')


def _load():
    try:
        mtime = _PATH.stat().st_mtime
    except OSError:
        return []
    if _CACHE['mtime'] == mtime:
        return _CACHE['items']
    try:
        data = json.loads(_PATH.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        data = []
    items = []
    for row in data if isinstance(data, list) else []:
        if not isinstance(row, dict):
            continue
        answer = str(row.get('answer') or '').strip()
        spot = str(row.get('spot') or '').strip()
        matches = [str(m) for m in (row.get('match') or []) if str(m).strip()]
        if answer and matches and spot:
            items.append({'spot': spot, 'matches': [_normalize(m) for m in matches], 'answer': answer})
    _CACHE['mtime'] = mtime
    _CACHE['items'] = items
    return items


def fixed_answer_for(spot, question):
    """返回与当前景点和问题匹配的固定回答；没有命中返回 None。"""
    name = str((spot or {}).get('spot_name') or '').strip()
    text = _normalize(question)
    if not name or not text:
        return None
    for item in _load():
        if item['spot'] not in (name, '*'):
            continue
        if any(text == m or m in text or text in m for m in item['matches']):
            return item['answer']
    return None
