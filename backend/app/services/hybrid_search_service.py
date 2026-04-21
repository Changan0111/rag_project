from typing import List, Dict, Optional
from app.services.milvus_service import milvus_service
from app.services.embedding_service import embedding_service
from app.services.bm25_service import bm25_service
from app.services.rerank_service import rerank_service
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class HybridSearchService:
    def __init__(self, rrf_k: int = 60, use_rerank: bool = None):
        self.rrf_k = rrf_k
        self.use_rerank = use_rerank if use_rerank is not None else settings.RERANK_ENABLED

    def _normalize_scores(self, results: List[dict]) -> List[dict]:
        if not results:
            return results

        scores = [r["score"] for r in results]
        max_score = max(scores) if scores else 1
        min_score = min(scores) if scores else 0
        score_range = max_score - min_score if max_score != min_score else 1

        for r in results:
            r["normalized_score"] = (r["score"] - min_score) / score_range

        return results

    def _rrf_fusion(
        self,
        vector_results: List[dict],
        bm25_results: List[dict],
        top_k: int = 5,
        vector_weight: float = 0.5
    ) -> List[dict]:
        doc_scores: Dict[int, dict] = {}

        for rank, result in enumerate(vector_results):
            doc_id = result["doc_id"]
            rrf_score = 1 / (self.rrf_k + rank + 1)

            if doc_id not in doc_scores:
                doc_scores[doc_id] = {
                    "doc_id": doc_id,
                    "content": result["content"],
                    "category": result.get("category"),
                    "vector_score": result.get("normalized_score", result["score"]),
                    "bm25_score": 0,
                    "vector_rank": rank + 1,
                    "bm25_rank": float('inf'),
                    "rrf_vector": rrf_score,
                    "rrf_bm25": 0
                }
            else:
                doc_scores[doc_id]["vector_score"] = result.get("normalized_score", result["score"])
                doc_scores[doc_id]["vector_rank"] = rank + 1
                doc_scores[doc_id]["rrf_vector"] = rrf_score

        for rank, result in enumerate(bm25_results):
            doc_id = result["doc_id"]
            rrf_score = 1 / (self.rrf_k + rank + 1)

            if doc_id not in doc_scores:
                doc_scores[doc_id] = {
                    "doc_id": doc_id,
                    "content": result["content"],
                    "category": result.get("category"),
                    "vector_score": 0,
                    "bm25_score": result.get("normalized_score", result["score"]),
                    "vector_rank": float('inf'),
                    "bm25_rank": rank + 1,
                    "rrf_vector": 0,
                    "rrf_bm25": rrf_score
                }
            else:
                doc_scores[doc_id]["bm25_score"] = result.get("normalized_score", result["score"])
                doc_scores[doc_id]["bm25_rank"] = rank + 1
                doc_scores[doc_id]["rrf_bm25"] = rrf_score

        for doc_id, doc in doc_scores.items():
            doc["rrf_score"] = vector_weight * doc["rrf_vector"] + (1 - vector_weight) * doc["rrf_bm25"]
            doc["hybrid_score"] = 0.5 * doc["vector_score"] + 0.5 * doc["bm25_score"]

        sorted_docs = sorted(doc_scores.values(), key=lambda x: x["rrf_score"], reverse=True)

        max_rrf = 1 / (self.rrf_k + 1)
        for doc in sorted_docs:
            doc["score"] = doc["rrf_score"] / max_rrf
            doc["raw_rrf_score"] = doc["rrf_score"]
            del doc["rrf_vector"]
            del doc["rrf_bm25"]

        return sorted_docs

    async def search(
        self,
        query: str,
        top_k: int = 5,
        category: Optional[str] = None,
        vector_weight: float = 0.5,
        use_rerank: Optional[bool] = None
    ) -> List[dict]:
        enable_rerank = use_rerank if use_rerank is not None else self.use_rerank
        
        candidate_multiplier = settings.RERANK_CANDIDATE_MULTIPLIER if enable_rerank else 1
        retrieval_top_k = settings.RETRIEVAL_TOP_K
        candidate_count = max(top_k * candidate_multiplier, retrieval_top_k)

        query_embedding = embedding_service.encode_single(query)

        vector_results = milvus_service.search(
            query_embedding=query_embedding,
            top_k=candidate_count,
            category=category
        )

        bm25_results = bm25_service.search(
            query=query,
            top_k=candidate_count,
            category=category
        )

        vector_results = self._normalize_scores(vector_results)
        bm25_results = self._normalize_scores(bm25_results)

        fused_results = self._rrf_fusion(
            vector_results=vector_results,
            bm25_results=bm25_results,
            top_k=candidate_count,
            vector_weight=vector_weight
        )

        if enable_rerank and len(fused_results) > top_k:
            fused_results = rerank_service.rerank(
                query=query,
                documents=fused_results,
                top_k=top_k
            )
            logger.info(f"Reranked results from {candidate_count} candidates to {top_k}")

        final_results = fused_results[:top_k]

        logger.info(
            f"Hybrid search completed: vector={len(vector_results)}, "
            f"bm25={len(bm25_results)}, "
            f"fused={len(fused_results)}, "
            f"final={len(final_results)}, "
            f"rerank_enabled={enable_rerank}"
        )

        return final_results

    def search_without_rerank(
        self,
        query: str,
        top_k: int = 5,
        category: Optional[str] = None,
        vector_weight: float = 0.5
    ) -> List[dict]:
        query_embedding = embedding_service.encode_single(query)

        vector_results = milvus_service.search(
            query_embedding=query_embedding,
            top_k=top_k,
            category=category
        )

        bm25_results = bm25_service.search(
            query=query,
            top_k=top_k,
            category=category
        )

        vector_results = self._normalize_scores(vector_results)
        bm25_results = self._normalize_scores(bm25_results)

        fused_results = self._rrf_fusion(
            vector_results=vector_results,
            bm25_results=bm25_results,
            top_k=top_k,
            vector_weight=vector_weight
        )

        return fused_results

    def index_document(self, doc_id: int, content: str, category: str = None):
        bm25_service.add_document(doc_id, content, category)
        logger.debug(f"Indexed document {doc_id} in BM25")

    def remove_document(self, doc_id: int):
        bm25_service.remove_document(doc_id)
        logger.debug(f"Removed document {doc_id} from BM25")

    def get_stats(self) -> dict:
        milvus_stats = milvus_service.get_collection_stats()
        return {
            "bm25": bm25_service.get_stats(),
            "milvus": milvus_stats,
            "rerank": {
                "enabled": rerank_service.is_enabled(),
                "model": settings.RERANK_MODEL
            }
        }


hybrid_search_service = HybridSearchService()
