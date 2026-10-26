"""A bounded, source-linked Qianlong-era interpretation, not a cloned person.

Only curated fact cards may speak in the historical role. Future events and
modern services are handed back to the modern guide; private thoughts are not
inferred. Chinese and English are authored against the same records.
"""
import hashlib
import re
from .tour_knowledge import dossier_for

ERA_END = 1795  # narrative boundary: end of the Qianlong era, not date of death
PARK = 'https://gygl.beijing.gov.cn/mlgy/mlgy_lsmy/201911/t20191129_732237.html'
BRIDGE = 'https://www.summerpalace.net.cn/laka_spot/detail/362.html'
CORRIDOR = 'https://www.summerpalace.net.cn/gallery.html'
RECORDS = [
    dict(id='qingyi-origin', year=1750, terms=r'清漪园|建园|修园|祝寿|万寿山|昆明湖|qingyi|garden|birthday|longevity hill|kunming', source=PARK,
         zh='1750年，为给母亲祝寿，乾隆改瓮山为万寿山、金海为昆明湖，并开始兴建行宫和庙宇。',
         en='In 1750, Qianlong renamed Wengshan as Longevity Hill and Jinhai as Kunming Lake, and began building palaces and temples to celebrate his mother’s birthday.'),
    dict(id='qingyi-name', year=1751, terms=r'园名|叫什么|命名|名字|名称|清漪园|named|name', source=PARK,
         zh='1751年，新园获名清漪园。',
         en='The garden was named Qingyi Yuan in 1751.'),
    dict(id='qingyi-complete', year=1764, terms=r'完工|完成|多久|多少年|finished|completed|how long', source=PARK,
         zh='清漪园工程于1764年全部完成。',
         en='Construction of Qingyi Yuan was completed in 1764.'),
    dict(id='corridor-founded', year=1750, terms=r'长廊|corridor', source=CORRIDOR,
         zh='长廊始建于1750年。', en='The Long Corridor was first built in 1750.'),
    dict(id='bridge-founded', year=1750, terms=r'十七孔桥|seventeen|17.arch', source=BRIDGE,
         zh='十七孔桥始建于1750年，连接东堤与南湖岛，以十七个桥券洞得名。',
         en='The Seventeen-Arch Bridge was first built in 1750. It connects the east embankment with South Lake Island and is named for its seventeen arches.'),
    dict(id='west-water', year=1749, terms=r'水利|水源|湖水|water supply|waterworks', source=PARK,
         zh='乾隆十四年整治北京西郊水利，将西山、玉泉山的泉水引入西湖，使湖水拓展至瓮山脚下。',
         en='In the fourteenth year of the Qianlong era, waterworks directed spring water from the Western Hills and Jade Spring Hill into the West Lake, extending the water to the foot of Wengshan.'),
]
MODERN = dict(id='later-history', year=1888, source=PARK,
    zh='清漪园在1860年遭英法联军焚毁，1886年开始重建，1888年改名颐和园。这些事件发生在本角色的年代范围之后。',
    en='Qingyi Yuan was burned by Anglo-French forces in 1860. Rebuilding began in 1886, and it was renamed the Summer Palace in 1888. These events fall after this character’s narrative period.')


def historical_answer(question, spot, language='zh', memory=None):
    q = question.lower()
    en = language == 'en'
    meta = dict(character='qianlong', label='乾隆时期·史料对话', era='1736–1795',
                portrayal='由当前数字导游演绎，非历史人物真实影像或原话', boundary_year=ERA_END,
                mode='historical', reason='', timeline=[])
    records = []
    if not dossier_for(spot):
        meta.update(mode='insufficient', reason='outside_catalog')
        answer = 'This character currently covers verified Qingyi Yuan history only.' if en else '这个角色目前只覆盖已核实的清漪园史料，这处景点暂未收录。'
    elif re.search(r'内心|心里|暗恋|梦到|梦见|私下|秘密|编个|编一|虚构|假装|忽略|原话|逐字|日记|最喜欢|心情|想法|private|secret|dream|invent|pretend|ignore|verbatim|favorite|favourite|feelings', q):
        meta.update(mode='insufficient', reason='no_private_evidence')
        answer = 'The selected sources do not establish those private thoughts or exact words. I can explain the documented events, but cannot invent a personal recollection.' if en else '现有史料没有记载这段私人想法或原话，我不能把想象说成亲历。可以继续问建园时间、园名或建筑沿革。'
    elif re.search(r'慈禧|光绪|咸丰|英法|焚毁|烧毁|重建|现代|今天|现在|手机|微信|互联网|地铁|人工智能|门票|厕所|开放|排队|cixi|guangxu|burn|rebuilt|rebuild|today|now|phone|internet|ticket|toilet|opening|queue|metro', q) or any(int(y)>ERA_END for y in re.findall(r'(?<!\d)(1\d{3}|20\d{2})(?!\d)',q)) or re.search(r'一八六零|一八八八|一九|二零|十九世纪|二十世纪|twentieth|nineteenth',q):
        meta.update(mode='modern_handoff', reason='outside_era')
        if re.search(r'慈禧|光绪|咸丰|英法|焚毁|烧毁|重建|1860|1886|1888|cixi|guangxu|burn|rebuilt|rebuild',q):
            records=[MODERN]; answer=MODERN['en' if en else 'zh']
        else:
            answer = 'This question belongs to modern times. I am handing it to the modern guide; current facilities and opening conditions require current information.' if en else '这个问题属于现代信息，交给现代导游回答。当日设施和开放情况需要依据当前资料。'
        answer = ('Modern guide: ' if en else '现代导游：') + answer
    elif re.search(r'谁画|谁写|作者|画师|工匠|花了多少|造价|多少钱|多高|多长|多少幅|几个亭|who painted|who wrote|artist|cost|how tall|how long is|how many paintings', q):
        meta.update(mode='insufficient', reason='no_matching_record')
        answer = 'The selected period sources do not establish that detail. I can explain the documented founding and naming, but cannot fill in the gap.' if en else '本角色收录的当时史料还不能确认这项细节。我可以讲已核实的始建时间和命名依据，不补写缺失的记录。'
    else:
        source_question = q
        if re.match(r'^(那|它|这个|继续|还有|then|it|what about|tell me more)',q):
            source_question += ' ' + (memory or {}).get('historical_question','')
        records = [r for r in RECORDS if re.search(r['terms'],source_question,re.I)]
        if not records and re.search(r'介绍|历史|讲讲|history|introduce|tell me',q):
            name = (spot or {}).get('spot_name','')
            records = [r for r in RECORDS if re.search(r['terms'],name)] or RECORDS[:1]
        if re.search(r'完工|完成|finished|completed',q) and not re.search(r'长廊|十七孔桥|corridor|bridge',source_question): records=[RECORDS[2]]
        elif re.search(r'园名|叫什么|命名|名字|名称|named|name',q) and not re.search(r'十七孔桥|bridge',q): records=[RECORDS[1]]
        elif re.search(r'水利|水源|water supply|waterworks',q): records=[RECORDS[5]]
        records = records[:2]
        if records:
            answer = ('In the Qianlong-era story: ' if en else '回到乾隆时期：') + ' '.join(r['en' if en else 'zh'] for r in records)
        else:
            meta.update(mode='insufficient',reason='no_matching_record')
            answer = 'I do not have a verified period source for that detail. You can ask about the garden’s founding, its name, the Long Corridor or the Seventeen-Arch Bridge.' if en else '这项细节还没有可核对的当时史料。你可以问建园、园名、长廊或十七孔桥，我会依据已有记录回答。'
    evidence=[]; sources={}
    for r in records:
        version=hashlib.sha256(r['zh'].encode()).hexdigest()[:16]
        title='颐和园官方景点资料' if 'summerpalace' in r['source'] else '北京市公园管理中心·颐和园'
        sources[r['source']]=dict(id=r['id'],title=title,url=r['source'])
        evidence.append(dict(id=r['id'], document=title, spot=(spot or {}).get('spot_name',''), topic='history',
                             excerpt=r['en' if en else 'zh'],version=version,retrieval_method='curated-era-facts',
                             source_url=r['source'],event_year=r['year']))
        meta['timeline'].append(dict(year=r['year'],text=r['en' if en else 'zh']))
    return answer, dict(persona=meta, evidence=evidence, sources=list(sources.values()),
                       verifiedOn='2026-10-13', evidenceNote='依据官方资料整理的事实摘要，非历史人物逐字原话。')
