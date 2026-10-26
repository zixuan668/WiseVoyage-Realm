"""Audience-specific explanations and conservative, auditable answer checks.

The numeric check detects unseen numeric literals, not semantic entailment.
It must never be presented as proof that every claim is factually correct.
"""
import re
import hashlib
from .tour_knowledge import dossier_for


def scenic_fact_evidence(spot, intents):
    """Expose the exact public DB fields supplied to generation for verification.

    A generated answer may use these fields even if a short FAQ fallback did
    not quote them. Keeping snapshots avoids rejecting supported elaboration.
    """
    if not spot or not set(intents)&{'overview','history','architecture','highlights','photography'}:
        return []
    fields={'description':'景点简介'}
    if set(intents)&{'overview','history','architecture','highlights'}:
        fields.update(history_detail='历史详情',tour_tips='游览提醒')
    if 'photography' in intents:fields['photo_tips']='拍照建议'
    records=[]
    for key,label in fields.items():
        text=spot.get(key)
        if not isinstance(text,str) or not text.strip():continue
        text=text[:6000]
        version=hashlib.sha256(text.encode()).hexdigest()[:16]
        records.append(dict(id='db-'+key+'-'+version,document='景点数据库 · '+label,
            spot=spot['spot_name'],topic=intents[0],excerpt=text,version=version,
            retrieval_method='database-field-snapshot',rank=0))
    return records

CHILD_OBSERVATIONS = {
    '仁寿殿':'仁寿殿是皇帝处理政事、接见来宾的地方。可以观察院落里的建筑怎样围着中间排列。',
    '长廊':'长廊是一条能遮阳避雨的长走廊，上面还有许多彩画。可以找一幅花鸟画，看看画里有什么。',
    '佛香阁':'佛香阁建在万寿山上，是园中很显眼的建筑。先从湖边观察它的位置，登山前请大人确认体力和台阶情况。',
    '昆明湖':'昆明湖是颐和园里的大湖，湖水和周围建筑一起组成园林风景。可以看看倒影和真实建筑有什么不同。',
    '十七孔桥':'十七孔桥连接湖岸和南湖岛，桥下有十七个桥洞。站在安全的岸边，试着数一数桥洞，别攀爬栏杆。',
    '苏州街':'苏州街模仿江南水乡的街道景色，商铺沿水布置。可以观察这里的桥与水的关系，临水处要跟紧大人。',
    '乐寿堂':'乐寿堂是慈禧在颐和园生活起居的重要地方。可以观察生活院落与处理政事的殿堂有哪些不同。',
    '玉澜堂':'玉澜堂与光绪皇帝的历史有关。先观察院子里的空间，再听导游说明历史事件，不能把影视剧情当成史实。',
    '排云殿':'排云殿位于万寿山前的建筑轴线上，与庆寿礼仪有关。可以找一找从湖岸向山上排列的建筑。',
    '谐趣园':'谐趣园像大园林里的一座小园林，有池塘、廊和亭。看看沿着池塘走时，眼前的景色怎样变化。',
    '石舫':'石舫外形像船，却是一座固定的园林建筑，不能开出去。可以观察它与湖上真正的船有什么区别。',
    '玉带桥':'玉带桥的桥拱很高，形状像一条弯弯的玉带。可以从岸边看桥的轮廓，过桥前请大人留意台阶。',
    '南湖岛':'南湖岛在昆明湖中，通过十七孔桥与东岸相连。可以看看岛上建筑与远处万寿山怎样共同组成景色。',
    '铜牛':'铜牛是一座与镇水寓意有关的铜制雕塑，它不是活的牛。可以观察它的姿态，但不要触摸或攀爬文物。',
    '德和园':'德和园的重要看点是大戏楼，过去用于观看戏曲演出。可以从外观观察舞台建筑，当天有没有演出要看公告。',
    '文昌阁':'文昌阁是一处具有城关形制的建筑，名称与文昌信仰有关。可以观察它与园内普通亭子形状有什么不同。',
}

AUDIENCE_POLICY = {
    'standard':'普通游客：介绍、历史、建筑和看点默认2至3个短段、220至420字，解释背景和可观察细节；具体数值、位置和设施问题直接回答。资料不足时宁可简短，不凑字数。',
    'child':'儿童讲解：使用小学生能懂的短句，解释生僻概念；可附一个安全的观察问题。严禁虚构人物对话、传说冒充史实或布置攀爬、触摸文物等任务。只回答所问主题，不把所有问题改成亲子介绍。',
    'deep':'深入讲解：分2至4个短段，围绕所问主题解释背景、证据和容易混淆的地方；只在证据存在时展开，不用篇幅掩盖未知。',
}


def child_fallback(turn, spot, fallback):
    if dossier_for(spot) and turn.intents == ['overview']:
        return CHILD_OBSERVATIONS.get(spot['spot_name'],fallback)
    return fallback


def numeric_literals(text):
    return {str(float(value)) for value in re.findall(r'(?<![A-Za-z])\d+(?:\.\d+)?',text)}


def unsupported_numbers(answer, evidence_text):
    return sorted(numeric_literals(answer)-numeric_literals(evidence_text))

