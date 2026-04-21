import logging
from typing import Tuple

from app.core.database import SessionLocal
from app.models import KnowledgeDoc
from app.services.bm25_service import bm25_service
from app.services.embedding_service import embedding_service
from app.services.milvus_service import milvus_service

logger = logging.getLogger(__name__)


class IndexBootstrapService:
    """
    启动时自动初始化索引：
    - BM25: 支持持久化，优先加载已保存的索引
    - Milvus: 以 doc_id 为维度做幂等同步（先删后插）
    """

    def bootstrap_knowledge_indexes(self, mode: str = "full") -> Tuple[int, int]:
        """
        Returns:
            (knowledge_doc_count, milvus_inserted_count)
        """
        mode = (mode or "full").strip().lower()
        if mode not in {"full", "if_empty"}:
            mode = "full"

        db = SessionLocal()
        try:
            docs = db.query(KnowledgeDoc).all()
            if not docs:
                bm25_service.clear()
                bm25_service.save_index()
                logger.info("No knowledge_docs found; cleared and saved BM25 index.")
                return 0, 0

            bm25_needs_bootstrap = True
            milvus_needs_bootstrap = True
            
            if mode == "if_empty":
                if bm25_service.load_index():
                    bm25_needs_bootstrap = False
                    logger.info("Loaded BM25 index from disk.")
                try:
                    milvus_needs_bootstrap = (milvus_service.get_collection_stats().get("num_entities", 0) == 0)
                except Exception:
                    milvus_needs_bootstrap = True

            if not bm25_needs_bootstrap and not milvus_needs_bootstrap:
                logger.info("Skip bootstrap: both BM25 and Milvus are already populated.")
                return len(docs), 0

            if bm25_needs_bootstrap:
                bm25_service.clear()
                for doc in docs:
                    bm25_service.add_document(
                        doc_id=doc.id,
                        content=doc.content,
                        category=doc.category,
                    )
                bm25_service.save_index()
                logger.info("BM25 index rebuilt and saved to disk.")

            inserted = 0
            if milvus_needs_bootstrap:
                texts = [doc.content for doc in docs]
                all_embeddings = embedding_service.encode(texts)

                doc_ids = []
                contents = []
                embeddings = []
                categories = []

                for i, doc in enumerate(docs):
                    if mode == "full":
                        try:
                            milvus_service.delete_by_doc_id(doc.id)
                        except Exception:
                            pass

                    doc_ids.append(doc.id)
                    contents.append((doc.content or "")[:2000])
                    embeddings.append(all_embeddings[i])
                    categories.append(doc.category or "")

                inserted = milvus_service.insert_vectors(
                    doc_ids=doc_ids,
                    contents=contents,
                    embeddings=embeddings,
                    categories=categories,
                )

            logger.info(
                "Bootstrapped knowledge indexes: mode=%s, docs=%s, milvus_inserted=%s, bm25_docs=%s",
                mode,
                len(docs),
                inserted,
                bm25_service.get_stats().get("doc_count"),
            )
            return len(docs), inserted
        finally:
            db.close()


index_bootstrap_service = IndexBootstrapService()

