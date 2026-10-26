import re
import hashlib
import math
from collections import Counter
from pathlib import Path
from typing import Any

from loguru import logger

from ....web_configs import WEB_CONFIGS

# 基础配置

# 景区导览 RAG 配置
TOUR_CONTEXT_MAX_LENGTH = 3600  # 景区知识库上下文最大长度
TOUR_GENERATE_TEMPLATE = (
    "【景区知识库资料】\n{}\n\n"
    "【游客问题】\n{}\n\n"
    "请根据以上景区资料回答游客的问题。要求：\n"
    "1. 第一段先直接回答问题；默认2-3句，明确要求详细时才展开；\n"
    "2. 资料中可能包含表格数据（用 | 分隔），请提取关键信息作答，不要原样输出管道符；\n"
    "3. 只使用与本轮景点和问题有关的资料；资料未记载的纹样、典故、年代、设施位置不得补写。"
    "缺少某项资料时只说明该项缺失，不要转去讲其他景区；\n"
    "4. 严禁出现【XX】格式的占位符，每个细节都要写具体。"
)  # 景区导览 RAG prompt 模板

# RAG 实例句柄
TOUR_RAG_RETRIEVER = None  # 景区知识库 RAG 实例


def document_chunk_counts(retriever):
    """Count the actual indexed fragments, without including synthetic spot records."""
    return Counter(source for source, _ in retriever.records)


def sync_knowledge_chunk_counts(user_id, retriever):
    from sqlmodel import Session, select
    from ...database.init_db import DB_ENGINE
    from ...models.tour_models import KnowledgeDocument
    counts = document_chunk_counts(retriever)
    with Session(DB_ENGINE) as db:
        docs = db.exec(select(KnowledgeDocument).where(
            KnowledgeDocument.user_id == user_id, KnowledgeDocument.status == 'completed'
        )).all()
        for doc in docs:
            doc.chunk_count = counts.get(Path(doc.file_path).name, 0)
            db.add(doc)
        db.commit()


class LightweightTourRetriever:
    """景点/主题过滤后的 BM25 + 字符 TF-IDF，使用 RRF 合并排名。

    不依赖常驻的大型 embedding/reranker 模型，适合比赛现场和普通笔记本；
    检索到的原文仍会进入大模型上下文，因此保持完整 RAG 工作流。
    """

    def __init__(self, records: list[tuple[str, str]]):
        from sklearn.feature_extraction.text import TfidfVectorizer

        self.records: list[tuple[str, str]] = []
        self.metadata: list[dict] = []
        from ..tour_knowledge import load_book
        names = set(load_book()["spots"])
        for source, text in records:
            # Keep entity and topic boundaries intact. Legacy documents with
            # named headings are supported, but unscoped fragments are never
            # allowed to answer a specific scenic-site question.
            spot, topic, buffer = "", "", []
            def flush():
                body="\n".join(buffer).strip()
                if body:
                    self.records.append((source,body))
                    self.metadata.append(dict(spot=spot,topic=topic))
                buffer.clear()
            for line in text.splitlines():
                marker=re.match(r"<!--\s*spot:(.+?);topic:(\w+)\s*-->",line)
                heading=re.match(r"^#{1,3}\s+(.+)",line)
                if marker:
                    flush()
                    spot,topic=marker.groups()
                    continue
                if heading:
                    flush()
                    title=heading[1].strip()
                    if title in names: spot,topic=title,""
                    if title=="资料来源": spot,topic="","sources"
                buffer.append(line)
                if len("\n".join(buffer))>=650 and re.search(r"[。！？]$",line): flush()
            flush()

        if not self.records:
            raise RuntimeError("景区知识库中没有可检索文本")

        self.vectorizer = TfidfVectorizer(analyzer="char", ngram_range=(1, 3), sublinear_tf=True)
        self.matrix = self.vectorizer.fit_transform([text for _, text in self.records])
        self.term_counts=[Counter(self._tokens(text)) for _,text in self.records]
        self.lengths=[sum(c.values()) for c in self.term_counts]
        self.average_length=sum(self.lengths)/len(self.lengths)
        frequencies=Counter(term for counts in self.term_counts for term in counts)
        self.idf={term:math.log(1+(len(self.records)-count+0.5)/(count+0.5)) for term,count in frequencies.items()}
        self.source_versions={source:hashlib.sha256(text.encode()).hexdigest()[:16] for source,text in records}
        self.index_version=hashlib.sha256(repr(sorted(self.source_versions.items())).encode()).hexdigest()[:16]

    @staticmethod
    def _tokens(text):
        tokens=[]
        for word in re.findall(r'[\u4e00-\u9fff]+|[A-Za-z0-9]+',text.lower()):
            tokens.extend([word[i:i+2] for i in range(len(word)-1)] if re.search(r'[\u4e00-\u9fff]',word) and len(word)>1 else [word])
        return tokens

    def search_evidence(self, question, spot_name='', topics=None, limit=5):
        from ..conversation_focus import expand_retrieval_query
        # Scope is an eligibility filter, not evidence that a fragment answers
        # a question. Remove the injected scenic-name prefix from scoring.
        question=re.sub(r'^景点：.*?。游客问题：', '', question)
        question=expand_retrieval_query(question)
        scores=(self.matrix @ self.vectorizer.transform([question]).T).toarray().ravel()
        eligible=[i for i,meta in enumerate(self.metadata) if meta['topic']!='sources'
                  and (not spot_name or meta['spot']==spot_name) and (not topics or meta['topic'] in topics)]
        terms=set(self._tokens(question))
        bm25={i:sum(self.idf.get(term,0)*self.term_counts[i].get(term,0)*2.5 /
                    (self.term_counts[i].get(term,0)+1.5*(0.25+0.75*self.lengths[i]/self.average_length)) for term in terms)
              for i in eligible}
        sparse=sorted((i for i in eligible if bm25[i]>0),key=lambda i:(-bm25[i],i))[:20]
        character=sorted((i for i in eligible if scores[i]>0.03),key=lambda i:(-scores[i],i))[:20]
        fusion=Counter()
        for ranking in (sparse,character):
            for rank,i in enumerate(ranking,1): fusion[i]+=1/(60+rank)
        selected=sorted(fusion,key=lambda i:(-fusion[i],i))[:limit]
        return [dict(id=hashlib.sha256((self.records[i][0]+'\n'+self.records[i][1]).encode()).hexdigest()[:16],
                     document=self.records[i][0],spot=self.metadata[i]['spot'],topic=self.metadata[i]['topic'],
                     excerpt=self.records[i][1],version=self.source_versions[self.records[i][0]],
                     retrieval_method='bm25-char-tfidf-rrf',rank=rank)
                for rank,i in enumerate(selected,1)]

    def get(self, fs_id: str = "tour_default", **_: Any):
        return self

    def query(self, question: str, context_max_length: int = TOUR_CONTEXT_MAX_LENGTH,
              spot_name: str = "", topics=None):
        selected=self.search_evidence(question,spot_name,topics)

        chunks: list[str] = []
        references: list[str] = []
        context = ""
        for item in selected:
            source,text=item['document'],item['excerpt']
            remaining = context_max_length - len(context)
            if remaining <= 0:
                break
            excerpt = text[:remaining]
            chunks.append(excerpt)
            context += f"【来源：{source}】\n{excerpt}\n"
            if source not in references:
                references.append(source)
        return "\n".join(chunks), context[:context_max_length], references


async def _load_lightweight_tour_retriever(user_id: int, file_paths=None) -> LightweightTourRetriever:
    from ...database.knowledge_doc_db import get_all_knowledge_file_paths
    from .file_operation import FileOperation

    records: list[tuple[str, str]] = []
    file_operator = FileOperation()
    for file_path in (await get_all_knowledge_file_paths(user_id) if file_paths is None else file_paths):
        source_path = Path(WEB_CONFIGS.SERVER_FILE_ROOT) / file_path
        if not source_path.exists():
            logger.warning(f"Knowledge file not found: {source_path}")
            continue
        if source_path.suffix.lower() in {".md", ".txt", ".text"}:
            text = source_path.read_text(encoding="utf-8", errors="ignore")
        else:
            text, error = file_operator.read(str(source_path))
            if error:
                logger.warning(f"Knowledge file read failed: {source_path}: {error}")
                continue
        if text and text.strip():
            records.append((source_path.name, text.strip()))

    from sqlmodel import Session, select
    from ...database.init_db import DB_ENGINE
    from ...models.tour_models import ScenicSpotInfo
    with Session(DB_ENGINE) as db:
        spots = db.exec(select(ScenicSpotInfo).where(ScenicSpotInfo.delete == False)).all()
        for spot in spots:
            for field, topic in (('history_detail', '历史文化 历史沿革'), ('photo_tips', '最佳打卡点 最佳拍摄点 摄影机位'),
                                 ('description', '自然风光 景观特色 介绍'), ('tour_tips', '游览建议'),
                                 ('service_facilities', '服务设施'), ('location', '景点位置')):
                value = getattr(spot, field, '')
                if value:
                    records.append((f'景点档案：{spot.spot_name} / {field}', f'{spot.spot_name} {topic}：{value}'))
    retriever = LightweightTourRetriever(records)
    logger.info(f"Lightweight tour RAG loaded: {len(records)} documents, {len(retriever.records)} chunks")
    return retriever




def build_tour_rag_prompt(rag_retriever: Any, spot_name: str, prompt: str, topics=None) -> tuple:
    """构建景区导览 RAG prompt

    Args:
        rag_retriever: RAG检索器实例
        spot_name: 当前景点名称
        prompt: 游客原始问题

    Returns:
        tuple: (增强后的prompt, 引用来源列表)
    """
    real_retriever = rag_retriever.get(fs_id="tour_default")

    if isinstance(real_retriever, tuple):
        logger.info(f" @@@ Tour RAG not ready: {real_retriever}")
        return prompt, []

    # 保留完整问题，同时补充口语问题对应的检索主题。
    from ..tour_intent import retrieval_topics
    query_expansions = retrieval_topics(prompt)
    for words, topic in (
        (("拍照", "摄影", "拍摄", "机位", "取景", "出片"), "拍摄建议 最佳拍照位置 机位"),
        (("历史", "故事", "典故", "由来"), "历史典故"),
        (("厕所", "卫生间", "洗手间", "餐饮", "休息"), "服务设施"),
        (("怎么走", "怎么到", "路线", "下一站"), "游览路线 交通位置"),
    ):
        if any(word in prompt for word in words):
            query_expansions.append(topic)
    # Human-readable query expansions are not the canonical metadata topic IDs.
    # Keep the caller's history/photography/etc. filter instead of replacing it.
    query_text = f"景点：{spot_name}。游客问题：{prompt}" + (' ' + ' '.join(query_expansions) if query_expansions else '')
    kwargs=dict(context_max_length=TOUR_CONTEXT_MAX_LENGTH-len(TOUR_GENERATE_TEMPLATE))
    if isinstance(real_retriever,LightweightTourRetriever): kwargs.update(spot_name=spot_name,topics=topics)
    chunk, db_context, references = real_retriever.query(query_text, **kwargs)
    logger.info(f"Tour db_context length: {len(db_context) if db_context else 0}")

    # A shared index must not override the active dossier with another park.
    if not isinstance(real_retriever,LightweightTourRetriever) and spot_name and db_context and spot_name not in db_context:
        return prompt, []
    if db_context is not None and len(db_context) > 1:
        prompt_rag = TOUR_GENERATE_TEMPLATE.format(db_context, prompt)
    else:
        logger.info("Tour db_context empty, using original prompt")
        prompt_rag = prompt
        references = []

    logger.info(f"Tour RAG references = {references}")
    logger.info("=" * 20)

    return prompt_rag, references


async def load_tour_rag_model(user_id):
    """Load the shared BM25 and character TF-IDF knowledge index."""
    global TOUR_RAG_RETRIEVER
    prepared = await _load_lightweight_tour_retriever(user_id)
    sync_knowledge_chunk_counts(user_id, prepared)
    TOUR_RAG_RETRIEVER = prepared


async def rebuild_tour_rag_db(user_id, db_name="tour_default"):
    """Prepare the replacement index before publishing it to visitor sessions."""
    global TOUR_RAG_RETRIEVER
    prepared = await _load_lightweight_tour_retriever(user_id)
    sync_knowledge_chunk_counts(user_id, prepared)
    # A private administrator must not replace the public park owner's index.
    if user_id == 1:
        TOUR_RAG_RETRIEVER = prepared
    logger.info("Lightweight tour RAG index refreshed")
