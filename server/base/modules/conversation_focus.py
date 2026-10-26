"""Small explicit entity memory and domain query normalization.

Keeps the physical route location separate from the subject being discussed.
No model-generated rewrite may silently move a visitor or invent a referent.
"""
import re

ALIASES = {'大长廊': '长廊', '十七洞桥': '十七孔桥', '十七孔大桥': '十七孔桥',
           '大佛阁': '佛香阁', '石头船': '石舫', '铜做的牛': '铜牛'}
FOLLOW = re.compile(r'^(?:那|它|这些|这个|这幅|那个|刚才|为什么|还有|继续|再|详细|简单|一句话|who|why|what about|and |it |those |that |tell me more)', re.I)

def normalize_question(text):
    for alias, name in ALIASES.items(): text = text.replace(alias, name)
    return text

def focus_names(question, active, memory, names):
    """Return explicit/comparison subjects, otherwise one unambiguous subject."""
    q = normalize_question(question)
    explicit = [n for n in names if n in q]
    recent = [x for x in memory.get('recent_subjects', []) if isinstance(x, str) and x in names]
    current = (active or {}).get('spot_name', '')
    previous = next((n for n in reversed(recent) if n != (explicit[0] if explicit else current)), '')
    if re.search(r'区别|比较|对比|有什么不同|difference|compare|different', q, re.I) and re.search(r'刚才|上一|之前|previous|last one|earlier',q,re.I):
        pair = explicit[:1] or ([current] if current else [])
        return q, pair + ([previous] if previous else []) , not bool(previous)
    if explicit: return q, explicit, False
    if re.search(r'下一站|下一个景点|next stop', q, re.I): return q, [], False
    if FOLLOW.search(q) and memory.get('active_spot_id') == (active or {}).get('spot_id') and recent:
        return q, [recent[-1]], False
    return q, [], False

def remember_subjects(memory, old_memory, subject, persona):
    recent = [n for n in old_memory.get('recent_subjects', []) if isinstance(n, str)]
    if subject:
        recent = [n for n in recent if n != subject] + [subject]
    memory['recent_subjects'] = recent[-4:]
    memory['persona'] = persona
    return memory


def expand_retrieval_query(question):
    """Auditable domain synonyms; deliberately not labelled dense embeddings."""
    q = normalize_question(question)
    synonyms = [(r'谁修的|谁建的|修于|啥时候修|多大年纪', '始建 年代 建造 历史'),
                (r'啥好看|有啥特别|值得看啥', '特色 看点 建筑'),
                (r'画了啥|画的什么|梁上.*画|彩绘', '彩画 题材 山水 花鸟 人物'),
                (r'歇脚|歇会|腿酸|走累', '休息 体力 台阶 通行'),
                (r'出片|照相|怎么照|拍好看', '拍照 摄影 机位 取景')]
    return (q + ' ' + ' '.join(words for pattern, words in synonyms if re.search(pattern, q))).strip()
