"""Regression suite for realistic tour questions; no keys, TTS or DB required."""
import json
import unittest
from pathlib import Path
from server.base.modules.tour_knowledge import load_book, dossier_for
from server.base.modules.tour_dialogue import resolve_turn, local_answer, updated_memory, spoken_answer, scoped_history

ROOT=Path(__file__).resolve().parents[2]
LOCATIONS=json.loads((ROOT/'data/summer_palace_locations.json').read_text(encoding='utf-8'))['spots']


def spot(name, id=1):
    return dict(spot_name=name,spot_id=id,city='北京',visit_duration=25,**LOCATIONS[name])


def answer(name,q,memory=None,next_spot=None):
    s=spot(name)
    t=resolve_turn(q,s,memory)
    a,refs=local_answer(t,s,next_spot)
    return t,a,refs


class TourDialogueTests(unittest.TestCase):
    def test_all_sixteen_dossiers_are_substantial_and_sourced(self):
        book=load_book()
        self.assertEqual(set(book['spots']),set(LOCATIONS))
        total=0
        for name,d in book['spots'].items():
            with self.subTest(name=name):
                self.assertGreater(len(json.dumps(d,ensure_ascii=False)),2200)
                self.assertGreaterEqual(len(d['qa']),8)
                self.assertGreaterEqual(len(d['sources']),2)
                self.assertEqual(d['verified_on'],'2026-10-11')
                self.assertTrue((ROOT/'static'/d['document_path']).exists())
                self.assertNotEqual(d['history'],d['overview'])
                total+=len(d['qa'])
        self.assertGreaterEqual(total,129)

    def test_recommended_questions_do_not_become_location_answers(self):
        for name in LOCATIONS:
            for q,expected in [('最佳拍照点在哪里？','photography'),('附近哪里有厕所？','facilities'),
                               ('下一站推荐去哪里？','next')]:
                with self.subTest(name=name,q=q):
                    t,a,_=answer(name,q,next_spot=spot('长廊',2))
                    self.assertEqual(t.intents,[expected])
                    self.assertNotIn('现在我们来到',a)
                    self.assertNotIn('以上内容来自',a)
                    self.assertFalse(a.startswith(name+'位于'))

    def test_forty_real_fact_questions(self):
        cases=[
            ('仁寿殿','名字是什么含义','仁者寿'),('仁寿殿','这里是干什么的','政务'),('仁寿殿','铜凤是什么','燃香'),
            ('长廊','有多长','728'),('长廊','共有多少间','273'),('长廊','彩画是什么题材','山水'),('长廊','四个亭子叫什么','留佳'),
            ('佛香阁','多高','41'),('佛香阁','几层','三层'),('佛香阁','它和智慧海差在哪','砖石'),
            ('昆明湖','湖心这个标号怎么回事','知春亭'),('昆明湖','这里是云南滇池吗','北京'),('昆明湖','西堤怎么分水面','西堤'),
            ('十七孔桥','为什么叫这个名字','十七'),('十七孔桥','有多长','150'),('十七孔桥','金光穿洞在哪看','西北'),
            ('十七孔桥','金光穿洞是专门设计的吗','没有'),('苏州街','这些是原建筑吗','复建'),('苏州街','为什么叫买卖街','商街'),
            ('苏州街','该怎么欣赏','桥上'),('乐寿堂','败家石是什么故事','民间'),('乐寿堂','室内陈设有什么','宝座'),
            ('玉澜堂','一直是寝宫吗','书堂'),('玉澜堂','现在展示什么','原状'),('玉澜堂','给小朋友怎么讲','房间'),
            ('排云殿','以前是寺庙吗','庆寿'),('排云殿','名字什么意思','云雾'),('排云殿','和佛香阁怎么联系','中轴'),
            ('谐趣园','是不是仿寄畅园','无锡'),('谐趣园','知鱼桥有什么典故','庄子'),('谐趣园','惠山园哪年改名','1811'),
            ('石舫','能开走吗','不能'),('石舫','清晏舫什么意思','安宁'),('石舫','有多长','36'),
            ('玉带桥','几个孔','单孔'),('玉带桥','玉做的吗','宝石'),('玉带桥','西堤六桥有哪些','界湖桥'),
            ('南湖岛','怎么上岛','十七孔桥'),('南湖岛','岛上有什么','涵虚堂'),('铜牛','为什么放湖边','镇水'),
            ('铜牛','什么时候铸造','1755'),('德和园','为何叫京剧摇篮','谭鑫培'),('文昌阁','就是博物馆吗','不是'),
        ]
        for name,q,expected in cases:
            with self.subTest(name=name,q=q):
                _,a,refs=answer(name,q)
                self.assertIn(expected,a)
                self.assertLess(len(a),400)

    def test_follow_up_expands_then_shortens_without_repeating_intro(self):
        t,a,_=answer('长廊','这里有什么历史故事？')
        mem=updated_memory(t,spot('长廊'),a)
        t2,a2,_=answer('长廊','再详细讲讲',mem)
        self.assertTrue(t2.follow_up)
        self.assertEqual(t2.intents,['history'])
        # Standard narration is now substantial. A follow-up must add fresh
        # evidence, rather than repeat the first answer just to be longer.
        self.assertGreater(len(a2),80)
        self.assertTrue(any(sentence not in a for sentence in a2.split('。') if len(sentence)>10))
        self.assertNotEqual(a,a2)
        t3,a3,_=answer('长廊','一句话说重点',updated_memory(t2,spot('长廊'),a2))
        self.assertTrue(t3.brief)
        self.assertLessEqual(len(a3),160)

    def test_switching_spot_clears_referent_but_keeps_explicit_needs(self):
        t,a,_=answer('长廊','我带孩子，这里怎么看')
        mem=updated_memory(t,spot('长廊'),a)
        new=spot('石舫',2)
        t2=resolve_turn('那为什么呢？',new,mem)
        self.assertTrue(t2.clarification)
        self.assertIn('带孩子',t2.memory['needs'])
        history=[dict(role='user',message='长廊'),dict(role='guide',message='728米',aiMeta=dict(spotContext='长廊')),
                 dict(role='user',message='石舫')]
        self.assertEqual(len(scoped_history(history,'石舫')),1)

    def test_multi_intent_preserves_every_requested_topic(self):
        t,a,_=answer('长廊','讲讲历史，另外哪里拍照好？')
        self.assertIn('history',t.intents)
        self.assertIn('photography',t.intents)
        self.assertIn('728',a)
        self.assertIn('人物照',a)

    def test_missing_information_is_not_invented(self):
        for name in LOCATIONS:
            _,a,_=answer(name,'今天开放吗，票价是多少？')
            self.assertIn('实时',a)
            self.assertNotRegex(a,r'\d+元')
        _,a,_=answer('长廊','这里有多少隐藏摄像头？')
        self.assertIn('还没有答案',a)
        _,a,_=answer('铜牛','什么魔法真的可以防洪？')
        self.assertNotIn('施法',a)
        self.assertIsNone(dossier_for(dict(spot_name='长廊',city='上海')))

    def test_speech_is_clean_and_bounded(self):
        text='## 介绍\n**这里是长廊**。'+('彩画需要保护。'*90)+'\n[资料](https://example.com/file)'
        speech=spoken_answer(text)
        self.assertLessEqual(len(speech),800)
        self.assertNotIn('https',speech)
        self.assertNotIn('**',speech)
        self.assertNotIn('##',speech)

    def test_negation_does_not_create_a_visitor_need(self):
        t,a,_=answer('长廊','我不带孩子')
        self.assertNotIn('带孩子',updated_memory(t,spot('长廊'),a)['needs'])

    def test_generic_faq_keywords_cannot_override_a_practical_intent(self):
        t,a,_=answer('玉澜堂','现在开放吗？')
        self.assertEqual(t.intents,['opening'])
        self.assertIn('实时',a)
        t,a,_=answer('长廊','彩画怎么拍照？')
        self.assertEqual(t.intents,['photography'])

    def test_long_unpunctuated_speech_is_still_bounded(self):
        self.assertLessEqual(len(spoken_answer('字'*3000)),800)


if __name__=='__main__': unittest.main()
