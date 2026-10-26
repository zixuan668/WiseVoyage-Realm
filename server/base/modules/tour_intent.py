"""导览问题的同义词，用于知识检索及离线回答。"""
PHOTO_WORDS = ('拍照', '拍摄', '摄影', '机位', '取景', '出片', '打卡', '照相', '拍图')
HISTORY_WORDS = ('历史', '文化', '故事', '典故', '由来', '来历', '年代', '建于', '建造')
NATURE_WORDS = ('自然', '风光', '风景', '景色', '山水', '生态', '植物', '花草')


def retrieval_topics(question):
    topics = []
    for words, topic in ((PHOTO_WORDS, '拍摄建议 最佳打卡点 最佳拍摄点 机位'),
                         (HISTORY_WORDS, '历史文化 历史沿革 典故'),
                         (NATURE_WORDS, '自然风光 景观特色 生态')):
        if any(word in question for word in words):
            topics.append(topic)
    return topics
