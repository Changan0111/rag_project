import logging
import math
import re
import unicodedata
from difflib import SequenceMatcher
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.database import SessionLocal
from app.core.config import settings
from app.models import ChatHistory, KnowledgeDoc
from app.services.embedding_service import embedding_service
from app.services.bm25_service import bm25_service
from app.services.hybrid_search_service import hybrid_search_service
from app.services.milvus_service import milvus_service
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class EvaluationService:
    def __init__(self):
        self.llm_service = LLMService()

    def _sanitize_score_value(self, value: Any) -> Optional[float]:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return None

        if not math.isfinite(numeric):
            return None

        return numeric

    def _sanitize_score_dict(self, scores: Dict[str, Any]) -> Dict[str, Optional[float]]:
        return {
            key: self._sanitize_score_value(value)
            for key, value in scores.items()
        }

    def _extract_score(self, text: str) -> float:
        text = text.strip()
        
        if not text:
            return 0.5
        
        match = re.search(r'(\d+\.?\d*)', text)
        if match:
            try:
                score = float(match.group(1))
                if score > 1:
                    score = score / 100
                return max(0.0, min(1.0, score))
            except ValueError:
                pass
        
        return 0.5

    def _has_meaningful_text(self, value: Any) -> bool:
        return isinstance(value, str) and bool(value.strip())

    def _normalize_text_for_match(self, text: Optional[str]) -> str:
        if not text:
            return ""
        text = unicodedata.normalize("NFKC", text).strip().lower()
        text = "".join(ch for ch in text if not unicodedata.category(ch).startswith("P"))
        text = re.sub(r"\s+", "", text)
        return text

    def _text_similarity(self, left: Optional[str], right: Optional[str]) -> float:
        left_normalized = self._normalize_text_for_match(left)
        right_normalized = self._normalize_text_for_match(right)
        if not left_normalized or not right_normalized:
            return 0.0
        if left_normalized == right_normalized:
            return 1.0
        if left_normalized in right_normalized or right_normalized in left_normalized:
            return 0.95
        return SequenceMatcher(None, left_normalized, right_normalized).ratio()

    async def evaluate_single(
        self,
        query: str,
        answer: str,
        contexts: List[str],
        ground_truth: Optional[str] = None
    ) -> Dict[str, float]:
        scores = {}
        
        faithfulness_score = await self._evaluate_faithfulness(query, answer, contexts)
        scores['faithfulness'] = faithfulness_score
        
        answer_relevancy_score = await self._evaluate_answer_relevancy(query, answer)
        scores['answer_relevancy'] = answer_relevancy_score
        
        context_precision_score = await self._evaluate_context_precision(query, contexts)
        scores['context_precision'] = context_precision_score
        
        scores['overall_score'] = round(sum(scores.values()) / len(scores), 4)
        
        return scores

    async def _evaluate_faithfulness(
        self,
        query: str,
        answer: str,
        contexts: List[str]
    ) -> float:
        if not contexts or not answer:
            return 0.0
        
        context_text = "\n".join(contexts)
        
        prompt = f"""请分析以下回答是否基于给定的上下文信息，是否存在幻觉（编造信息）。

上下文信息：
{context_text}

用户问题：{query}

回答：{answer}

请判断：
1. 回答中的每个关键信息点是否都能在上下文中找到依据
2. 回答是否包含上下文中没有的信息（幻觉）

请给出一个0到1之间的分数：
- 1.0：完全基于上下文，无幻觉
- 0.7-0.9：大部分基于上下文，少量推断
- 0.4-0.6：部分基于上下文，存在一些幻觉
- 0.1-0.3：大量幻觉
- 0.0：完全编造

只返回分数数字，不要其他内容。"""

        try:
            result = await self.llm_service.generate(
                prompt=prompt,
                system_prompt="你是一个专业的RAG系统评估专家。",
                temperature=0.1
            )
            score = self._extract_score(result)
            return score
        except Exception as e:
            logger.error(f"Faithfulness evaluation failed: {e}")
            return 0.5

    async def _evaluate_answer_relevancy(
        self,
        query: str,
        answer: str
    ) -> float:
        if not answer or not query:
            return 0.0
        
        prompt = f"""请评估以下回答与用户问题的相关性。

用户问题：{query}

回答：{answer}

请判断：
1. 回答是否直接回应了用户的问题
2. 回答是否提供了用户需要的信息
3. 回答是否切题，没有跑题

请给出一个0到1之间的分数：
- 1.0：完全相关，直接回答问题
- 0.7-0.9：高度相关，基本回答了问题
- 0.4-0.6：部分相关，回答了一些相关内容
- 0.1-0.3：相关性低，回答偏离问题
- 0.0：完全不相关

只返回分数数字，不要其他内容。"""

        try:
            result = await self.llm_service.generate(
                prompt=prompt,
                system_prompt="你是一个专业的RAG系统评估专家。",
                temperature=0.1
            )
            score = self._extract_score(result)
            return score
        except Exception as e:
            logger.error(f"Answer relevancy evaluation failed: {e}")
            return 0.5

    async def _evaluate_context_precision(
        self,
        query: str,
        contexts: List[str]
    ) -> float:
        if not contexts:
            return 0.0

        try:
            relevance_list = []
            for i, context in enumerate(contexts):
                prompt = f"""请严格判断以下检索到的上下文片段是否能直接回答用户问题。

用户问题：{query}

上下文片段{i+1}：{context}

【判断标准 - 请严格遵循】
- 上下文中包含的必须是回答问题所需的**具体内容/数据/步骤**
- 如果上下文说的是"同领域的其他内容"（如用户问退货流程，上下文说的是维修流程），应给低分
- 如果上下文只包含**规则/政策**但用户问的是**操作步骤**，应给中低分（0.3-0.5）
- 即使上下文和问题的主题相关，但讨论的是问题的**不同方面**，不应给高分

【评分标准】
- 1.0：上下文包含了回答用户问题所需的**全部关键信息**
- 0.7-0.9：上下文包含大部分回答所需信息，但缺少少量细节或有少量无关内容
- 0.4-0.6：上下文只包含回答所需信息的**一部分**，或大部分内容不直接相关
- 0.1-0.3：上下文主题相关但不能帮助回答该具体问题（如用户问流程，上下文说的是政策）
- 0.0：上下文完全不相关

只返回分数数字，不要其他内容。"""
                result = await self.llm_service.generate(
                    prompt=prompt,
                    system_prompt="你是一个严格的RAG系统评估专家，请严格按照判断标准评分，不要给间接相关的内容打高分。",
                    temperature=0.1
                )
                score = self._extract_score(result)
                relevance_list.append(score)

            if not relevance_list:
                return 0.0

            relevant_items = [(k, s) for k, s in enumerate(relevance_list, 1) if s >= 0.5]

            if not relevant_items:
                return 0.0

            precision_at_k = []
            cumulative = 0.0
            for k, score in enumerate(relevance_list, 1):
                if score >= 0.5:
                    cumulative += score
                    precision_at_k.append(cumulative / k)

            total_relevance = sum(s for s in relevance_list if s >= 0.5)

            if total_relevance == 0:
                return 0.0

            context_precision = sum(precision_at_k) / total_relevance

            return self._clip_score(context_precision)
        except Exception as e:
            logger.error(f"Context precision evaluation failed: {e}")
            return 0.5

    async def _evaluate_context_recall(
        self,
        ground_truth: str,
        contexts: List[str]
    ) -> float:
        if not contexts or not ground_truth:
            return 0.0
        
        context_text = "\n".join(contexts)
        
        prompt = f"""请评估检索到的上下文是否包含了回答标准答案所需的信息。

标准答案：{ground_truth}

检索到的上下文：
{context_text}

请判断上下文是否包含了标准答案中的关键信息点。

请给出一个0到1之间的分数：
- 1.0：上下文包含所有必要信息
- 0.7-0.9：上下文包含大部分必要信息
- 0.4-0.6：上下文包含部分必要信息
- 0.1-0.3：上下文包含少量必要信息
- 0.0：上下文完全不相关

只返回分数数字，不要其他内容。"""

        try:
            result = await self.llm_service.generate(
                prompt=prompt,
                system_prompt="你是一个专业的RAG系统评估专家。",
                temperature=0.1
            )
            score = self._extract_score(result)
            return score
        except Exception as e:
            logger.error(f"Context recall evaluation failed: {e}")
            return 0.5

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        import numpy as np
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(dot_product / (norm1 * norm2))

    def _clip_score(self, value: float) -> float:
        return max(0.0, min(1.0, float(value)))

    def _get_embedding_with_cache(
        self,
        text: Optional[str],
        embedding_cache: Dict[str, List[float]]
    ) -> Optional[List[float]]:
        normalized_text = (text or "").strip()
        if not normalized_text:
            return None

        if normalized_text not in embedding_cache:
            embedding = embedding_service.encode_single(normalized_text)
            if hasattr(embedding, "tolist"):
                embedding = embedding.tolist()
            embedding_cache[normalized_text] = embedding

        return embedding_cache[normalized_text]

    def _embedding_similarity(
        self,
        left: Optional[str],
        right: Optional[str],
        embedding_cache: Dict[str, List[float]]
    ) -> float:
        try:
            left_embedding = self._get_embedding_with_cache(left, embedding_cache)
            right_embedding = self._get_embedding_with_cache(right, embedding_cache)
            if not left_embedding or not right_embedding:
                return 0.0
            return self._clip_score(self._cosine_similarity(left_embedding, right_embedding))
        except Exception as e:
            logger.warning(f"Failed to compute embedding similarity: {e}")
            return 0.0

    def _evaluate_context_precision_proxy(
        self,
        query: str,
        contexts: List[str],
        embedding_cache: Dict[str, List[float]]
    ) -> float:
        if not contexts:
            return 0.0

        relevance_scores = [
            self._embedding_similarity(query, context, embedding_cache)
            for context in contexts
            if self._has_meaningful_text(context)
        ]
        if not relevance_scores:
            return 0.0

        n = len(relevance_scores)
        position_weights = [1.0 / (i + 1) for i in range(n)]
        total_weight = sum(position_weights)

        weighted_sum = sum(s * w for s, w in zip(relevance_scores, position_weights))

        context_precision = weighted_sum / total_weight

        return self._clip_score(context_precision)

    def _evaluate_context_recall_proxy(
        self,
        ground_truth: Optional[str],
        contexts: List[str],
        embedding_cache: Dict[str, List[float]]
    ) -> float:
        if not self._has_meaningful_text(ground_truth) or not contexts:
            return 0.0

        valid_contexts = [context for context in contexts if self._has_meaningful_text(context)]
        if not valid_contexts:
            return 0.0

        merged_context = "\n".join(valid_contexts)
        merged_similarity = self._embedding_similarity(ground_truth, merged_context, embedding_cache)
        context_similarities = [
            self._embedding_similarity(ground_truth, context, embedding_cache)
            for context in valid_contexts
        ]
        lexical_similarity = max(
            [self._text_similarity(ground_truth, merged_context)]
            + [self._text_similarity(ground_truth, context) for context in valid_contexts]
        )

        score = max(
            merged_similarity,
            max(context_similarities) if context_similarities else 0.0,
            lexical_similarity
        )
        return self._clip_score(score)

    async def _retrieve_contexts_by_mode(
        self,
        query: str,
        top_k: int,
        retrieval_mode: str,
        vector_weight: float = 0.5
    ) -> List[str]:
        retrieval_mode = retrieval_mode.lower()

        try:
            if retrieval_mode == "vector":
                query_embedding = embedding_service.encode_single(query)
                results = milvus_service.search(query_embedding, top_k=top_k)
            elif retrieval_mode == "bm25":
                results = bm25_service.search(query=query, top_k=top_k)
            elif retrieval_mode == "hybrid":
                results = await hybrid_search_service.search(
                    query=query,
                    top_k=top_k,
                    vector_weight=vector_weight,
                    use_rerank=False
                )
            elif retrieval_mode == "hybrid_rerank":
                results = await hybrid_search_service.search(
                    query=query,
                    top_k=top_k,
                    vector_weight=vector_weight,
                    use_rerank=True
                )
            else:
                raise ValueError(f"Unsupported retrieval mode: {retrieval_mode}")

            return [item.get("content", "") for item in results if item.get("content")]
        except Exception as e:
            logger.warning(
                f"Failed to retrieve contexts for mode={retrieval_mode}, top_k={top_k}, "
                f"vector_weight={vector_weight}: {e}"
            )
            return []

    async def compare_recall_configs(
        self,
        db: Session,
        sample_limit: int = 5,
        top_ks: Optional[List[int]] = None,
        retrieval_modes: Optional[List[str]] = None,
        vector_weights: Optional[List[float]] = None,
        similarity_threshold: float = 0.75
    ) -> Dict[str, Any]:
        from app.models import EvaluationDataset

        top_ks = sorted({int(value) for value in (top_ks or [3, 5, 10]) if int(value) > 0})
        retrieval_modes = [mode.lower() for mode in (retrieval_modes or ["vector", "bm25", "hybrid", "hybrid_rerank"])]
        retrieval_modes = [mode for mode in retrieval_modes if mode in {"vector", "bm25", "hybrid", "hybrid_rerank"}]
        vector_weights = sorted({
            round(float(value), 2)
            for value in (vector_weights or [0.3, 0.5, 0.7])
            if 0 <= float(value) <= 1
        })
        similarity_threshold = self._clip_score(similarity_threshold)

        if not top_ks:
            raise ValueError("top_ks must contain at least one positive integer")
        if not retrieval_modes:
            raise ValueError("retrieval_modes must contain at least one valid mode")
        if "hybrid" in retrieval_modes and not vector_weights:
            raise ValueError("vector_weights must contain at least one value for hybrid mode")

        dataset_items = db.query(EvaluationDataset).order_by(desc(EvaluationDataset.created_at)).limit(sample_limit).all()
        if not dataset_items:
            raise ValueError("evaluation_dataset is empty, please add dataset samples first")

        samples = [{
            "question": item.question,
            "ground_truth": item.ground_truth,
            "category": item.category
        } for item in dataset_items if self._has_meaningful_text(item.question) and self._has_meaningful_text(item.ground_truth)]

        if not samples:
            raise ValueError("evaluation_dataset has no valid question and ground_truth pairs")

        embedding_cache: Dict[str, List[float]] = {}
        experiments = []

        for retrieval_mode in retrieval_modes:
            experiment_weights = vector_weights if retrieval_mode == "hybrid" else [None]
            for top_k in top_ks:
                for vector_weight in experiment_weights:
                    config_label = (
                        f"{retrieval_mode.upper()} · Top-{top_k} · Weight-{vector_weight:.1f}"
                        if vector_weight is not None
                        else f"{retrieval_mode.upper()} · Top-{top_k}"
                    )

                    recall_scores = []
                    precision_scores = []
                    hit_count = 0
                    total_context_count = 0
                    sample_results = []

                    for sample in samples:
                        contexts = await self._retrieve_contexts_by_mode(
                            query=sample["question"],
                            top_k=top_k,
                            retrieval_mode=retrieval_mode,
                            vector_weight=vector_weight or 0.5
                        )
                        context_precision = self._evaluate_context_precision_proxy(
                            sample["question"],
                            contexts,
                            embedding_cache
                        )
                        context_recall = self._evaluate_context_recall_proxy(
                            sample["ground_truth"],
                            contexts,
                            embedding_cache
                        )
                        is_hit = context_recall >= similarity_threshold

                        recall_scores.append(context_recall)
                        precision_scores.append(context_precision)
                        total_context_count += len(contexts)
                        if is_hit:
                            hit_count += 1

                        sample_results.append({
                            "question": sample["question"],
                            "ground_truth": sample["ground_truth"],
                            "contexts": contexts,
                            "context_count": len(contexts),
                            "context_recall": round(context_recall, 4),
                            "context_precision": round(context_precision, 4),
                            "is_hit": is_hit
                        })

                    sample_count = len(sample_results)
                    average_recall = round(sum(recall_scores) / sample_count, 4) if sample_count else 0.0
                    average_precision = round(sum(precision_scores) / sample_count, 4) if sample_count else 0.0
                    hit_rate = round(hit_count / sample_count, 4) if sample_count else 0.0
                    average_context_count = round(total_context_count / sample_count, 2) if sample_count else 0.0

                    experiments.append({
                        "config_label": config_label,
                        "retrieval_mode": retrieval_mode,
                        "top_k": top_k,
                        "vector_weight": vector_weight,
                        "sample_count": sample_count,
                        "average_context_recall": average_recall,
                        "average_context_precision": average_precision,
                        "hit_rate": hit_rate,
                        "average_context_count": average_context_count,
                        "samples": sample_results
                    })

        experiments.sort(
            key=lambda item: (
                item["average_context_recall"],
                item["hit_rate"],
                item["average_context_precision"]
            ),
            reverse=True
        )

        best_experiment = experiments[0] if experiments else None

        return {
            "sample_count": len(samples),
            "config_count": len(experiments),
            "similarity_threshold": similarity_threshold,
            "metric_note": "该板块使用 ground_truth 与召回上下文的相似度近似衡量召回表现，适合做多配置快速对比。",
            "best_experiment": {
                "config_label": best_experiment["config_label"],
                "average_context_recall": best_experiment["average_context_recall"],
                "average_context_precision": best_experiment["average_context_precision"],
                "hit_rate": best_experiment["hit_rate"]
            } if best_experiment else None,
            "experiments": experiments
        }

    def _normalize_doc_ids(self, values: Any) -> List[int]:
        if not isinstance(values, list):
            return []

        normalized = []
        seen = set()
        for value in values:
            try:
                doc_id = int(value)
            except (TypeError, ValueError):
                continue

            if doc_id <= 0 or doc_id in seen:
                continue

            seen.add(doc_id)
            normalized.append(doc_id)

        return normalized

    async def _retrieve_strict_results_by_mode(
        self,
        query: str,
        top_k: int,
        retrieval_mode: str,
        vector_weight: float = 0.5
    ) -> List[Dict[str, Any]]:
        retrieval_mode = retrieval_mode.lower()

        try:
            if retrieval_mode == "vector":
                query_embedding = embedding_service.encode_single(query)
                return milvus_service.search(query_embedding, top_k=top_k)
            if retrieval_mode == "bm25":
                return bm25_service.search(query=query, top_k=top_k)
            if retrieval_mode == "hybrid":
                return await hybrid_search_service.search(
                    query=query,
                    top_k=top_k,
                    vector_weight=vector_weight,
                    use_rerank=False
                )
            if retrieval_mode == "hybrid_rerank":
                return await hybrid_search_service.search(
                    query=query,
                    top_k=top_k,
                    vector_weight=vector_weight,
                    use_rerank=True
                )
            raise ValueError(f"Unsupported retrieval mode: {retrieval_mode}")
        except Exception as e:
            logger.warning(
                f"Failed to retrieve strict recall results for mode={retrieval_mode}, "
                f"top_k={top_k}, vector_weight={vector_weight}: {e}"
            )
            return []

    async def compare_strict_recall_configs(
        self,
        db: Session,
        sample_limit: int = 5,
        top_ks: Optional[List[int]] = None,
        retrieval_modes: Optional[List[str]] = None,
        vector_weights: Optional[List[float]] = None,
        best_sort_by: str = "hit_rate"
    ) -> Dict[str, Any]:
        import time
        from app.models import EvaluationDataset

        top_ks = sorted({int(value) for value in (top_ks or [3, 5, 10]) if int(value) > 0})
        retrieval_modes = [mode.lower() for mode in (retrieval_modes or ["vector", "bm25", "hybrid", "hybrid_rerank"])]
        retrieval_modes = [mode for mode in retrieval_modes if mode in {"vector", "bm25", "hybrid", "hybrid_rerank"}]
        vector_weights = sorted({
            round(float(value), 2)
            for value in (vector_weights or [0.3, 0.5, 0.7])
            if 0 <= float(value) <= 1
        })

        if not top_ks:
            raise ValueError("top_ks must contain at least one positive integer")
        if not retrieval_modes:
            raise ValueError("retrieval_modes must contain at least one valid mode")
        if ("hybrid" in retrieval_modes or "hybrid_rerank" in retrieval_modes) and not vector_weights:
            raise ValueError("vector_weights must contain at least one value for hybrid mode")

        dataset_items = db.query(EvaluationDataset).order_by(desc(EvaluationDataset.created_at)).limit(sample_limit).all()
        if not dataset_items:
            raise ValueError("evaluation_dataset is empty, please add dataset samples first")

        samples = [{
            "question": item.question,
            "ground_truth": item.ground_truth,
            "category": item.category,
            "relevant_doc_ids": self._normalize_doc_ids(getattr(item, "relevant_doc_ids", []))
        } for item in dataset_items if self._has_meaningful_text(item.question)]
        samples = [sample for sample in samples if sample["relevant_doc_ids"]]

        if not samples:
            raise ValueError("evaluation_dataset has no valid relevant_doc_ids annotations")

        single_label_mode = all(len(sample["relevant_doc_ids"]) == 1 for sample in samples)
        experiments = []
        best_sort_by = (best_sort_by or "hit_rate").strip().lower()
        if best_sort_by not in {"hit_rate", "mrr"}:
            best_sort_by = "hit_rate"

        for retrieval_mode in retrieval_modes:
            experiment_weights = vector_weights if retrieval_mode == "hybrid" else [None]
            for top_k in top_ks:
                for vector_weight in experiment_weights:
                    config_label = (
                        f"{retrieval_mode.upper()} / Top-{top_k} / Weight-{vector_weight:.1f}"
                        if vector_weight is not None
                        else f"{retrieval_mode.upper()} / Top-{top_k}"
                    )

                    recall_scores = []
                    precision_scores = []
                    reciprocal_ranks = []
                    hit_count = 0
                    total_retrieved_count = 0
                    response_times = []
                    sample_results = []

                    for sample in samples:
                        start_time = time.time()
                        
                        results = await self._retrieve_strict_results_by_mode(
                            query=sample["question"],
                            top_k=top_k,
                            retrieval_mode=retrieval_mode,
                            vector_weight=vector_weight or 0.5
                        )
                        
                        end_time = time.time()
                        response_time_ms = (end_time - start_time) * 1000
                        response_times.append(response_time_ms)
                        
                        retrieved_doc_ids = self._normalize_doc_ids(
                            [item.get("doc_id") for item in results]
                        )
                        matched_doc_ids = [
                            doc_id for doc_id in retrieved_doc_ids
                            if doc_id in sample["relevant_doc_ids"]
                        ]
                        first_hit_rank = next(
                            (
                                index + 1
                                for index, doc_id in enumerate(retrieved_doc_ids)
                                if doc_id in sample["relevant_doc_ids"]
                            ),
                            None
                        )

                        recall_at_k = len(set(matched_doc_ids)) / len(sample["relevant_doc_ids"])
                        precision_at_k = len(set(matched_doc_ids)) / top_k
                        is_hit = bool(matched_doc_ids)
                        reciprocal_rank = round(1 / first_hit_rank, 4) if first_hit_rank else 0.0

                        recall_scores.append(recall_at_k)
                        precision_scores.append(precision_at_k)
                        reciprocal_ranks.append(reciprocal_rank)
                        total_retrieved_count += len(retrieved_doc_ids)
                        if is_hit:
                            hit_count += 1

                        sample_results.append({
                            "question": sample["question"],
                            "ground_truth": sample["ground_truth"],
                            "relevant_doc_ids": sample["relevant_doc_ids"],
                            "retrieved_doc_ids": retrieved_doc_ids,
                            "matched_doc_ids": list(dict.fromkeys(matched_doc_ids)),
                            "retrieved_docs": [{
                                "doc_id": item.get("doc_id"),
                                "title": item.get("title"),
                                "category": item.get("category"),
                                "content": item.get("content", "")
                            } for item in results],
                            "retrieved_count": len(retrieved_doc_ids),
                            "recall_at_k": round(recall_at_k, 4),
                            "precision_at_k": round(precision_at_k, 4),
                            "first_hit_rank": first_hit_rank,
                            "reciprocal_rank": reciprocal_rank,
                            "is_hit": is_hit,
                            "response_time_ms": round(response_time_ms, 2)
                        })

                    sample_count = len(sample_results)
                    average_recall = round(sum(recall_scores) / sample_count, 4) if sample_count else 0.0
                    average_precision = round(sum(precision_scores) / sample_count, 4) if sample_count else 0.0
                    hit_rate = round(hit_count / sample_count, 4) if sample_count else 0.0
                    mrr = round(sum(reciprocal_ranks) / sample_count, 4) if sample_count else 0.0
                    average_retrieved_count = round(total_retrieved_count / sample_count, 2) if sample_count else 0.0
                    avg_response_time = round(sum(response_times) / len(response_times), 2) if response_times else 0.0

                    experiments.append({
                        "config_label": config_label,
                        "retrieval_mode": retrieval_mode,
                        "top_k": top_k,
                        "vector_weight": vector_weight,
                        "sample_count": sample_count,
                        "average_recall_at_k": average_recall,
                        "average_precision_at_k": average_precision,
                        "hit_rate": hit_rate,
                        "mrr": mrr,
                        "average_retrieved_count": average_retrieved_count,
                        "avg_response_time_ms": avg_response_time,
                        "samples": sample_results
                    })

        def _sort_key(item: Dict[str, Any]):
            if best_sort_by == "mrr":
                primary = item.get("mrr", 0.0)
            else:
                primary = item.get("hit_rate", 0.0)

            # 次级指标保持稳定，避免同分时随机跳动
            return (
                primary,
                item.get("mrr", 0.0),
                item.get("hit_rate", 0.0),
                item.get("average_recall_at_k", 0.0),
                item.get("average_precision_at_k", 0.0),
            )

        experiments.sort(key=_sort_key, reverse=True)

        best_experiment = experiments[0] if experiments else None

        return {
            "sample_count": len(samples),
            "config_count": len(experiments),
            "single_label_mode": single_label_mode,
            "best_sort_by": best_sort_by,
            "primary_metrics": (
                ["mrr", "hit_rate"] if best_sort_by == "mrr"
                else ["hit_rate", "mrr"]
            ),
            "metric_note": (
                "当前数据集按单标签方式标注时，Recall@K 与 Hit@K 等价，"
                "Precision@K 会因每题最多只有 1 个标准相关文档而天然偏低，建议以 Hit@K 和 MRR 作为主指标。"
                if single_label_mode
                else "当前结果按 relevant_doc_ids 标注计算，可同时参考 Recall@K、Hit@K、Precision@K 和 MRR。"
            ),
            "best_experiment": {
                "config_label": best_experiment["config_label"],
                "average_recall_at_k": best_experiment["average_recall_at_k"],
                "average_precision_at_k": best_experiment["average_precision_at_k"],
                "hit_rate": best_experiment["hit_rate"],
                "mrr": best_experiment["mrr"],
                "avg_response_time_ms": best_experiment.get("avg_response_time_ms")
            } if best_experiment else None,
            "experiments": experiments
        }

    def _match_ground_truth(self, query: str, dataset_items: List[Any]) -> Optional[str]:
        if not dataset_items:
            return None

        normalized_query = self._normalize_text_for_match(query)
        for item in dataset_items:
            if self._normalize_text_for_match(getattr(item, "question", "")) == normalized_query:
                logger.info(f"Matched query '{query}' with dataset item by normalized text equality")
                return item.ground_truth

        best_text_match = None
        best_text_similarity = 0.0
        for item in dataset_items:
            similarity = self._text_similarity(query, getattr(item, "question", ""))
            if similarity > best_text_similarity:
                best_text_similarity = similarity
                best_text_match = item

        if best_text_match and best_text_similarity >= 0.88:
            logger.info(
                f"Matched query '{query}' with dataset item by text similarity: {best_text_similarity:.4f}"
            )
            return best_text_match.ground_truth

        embedding_candidates = [item for item in dataset_items if getattr(item, "question_embedding", None)]
        if not embedding_candidates:
            logger.warning(
                f"No dataset question embeddings available when matching ground_truth for query '{query}'"
            )
            return None

        try:
            query_embedding = embedding_service.encode_single(query)
        except Exception as e:
            logger.warning(f"Failed to encode query for ground_truth matching: {e}")
            return None

        best_match = None
        best_similarity = 0.0
        similarity_threshold = 0.85

        for item in embedding_candidates:
            item_embedding = item.question_embedding
            if isinstance(item_embedding, str):
                import json
                item_embedding = json.loads(item_embedding)

            similarity = self._cosine_similarity(query_embedding, item_embedding)
            if similarity > best_similarity:
                best_similarity = similarity
                best_match = item

        if best_match and best_similarity >= similarity_threshold:
            logger.info(
                f"Matched query '{query}' with dataset item by embedding similarity: {best_similarity:.4f}"
            )
            return best_match.ground_truth

        return None

    def _hydrate_ground_truths_for_samples(
        self,
        samples: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        if not samples:
            return samples

        samples = [dict(sample) for sample in samples]
        missing_indices = [
            i for i, sample in enumerate(samples)
            if not self._has_meaningful_text(sample.get('ground_truth'))
            and self._has_meaningful_text(sample.get('query'))
        ]
        if not missing_indices:
            return samples

        from app.models import EvaluationDataset

        db = SessionLocal()
        try:
            dataset_items = db.query(EvaluationDataset).all()
            if not dataset_items:
                logger.warning("Evaluation dataset is empty, unable to hydrate missing ground_truth values")
                return samples

            hydrated_count = 0
            for index in missing_indices:
                ground_truth = self._match_ground_truth(samples[index].get('query', ''), dataset_items)
                if self._has_meaningful_text(ground_truth):
                    samples[index]['ground_truth'] = ground_truth
                    hydrated_count += 1

            logger.info(
                f"Hydrated ground_truth for {hydrated_count}/{len(missing_indices)} samples before RAGAS evaluation"
            )
            return samples
        except Exception as e:
            logger.warning(f"Failed to hydrate ground_truth values before RAGAS evaluation: {e}")
            return samples
        finally:
            db.close()

    async def evaluate_batch(
        self,
        db: Session,
        session_ids: Optional[List[str]] = None,
        limit: int = 10,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        from app.models import EvaluationDataset
        
        query = db.query(ChatHistory).filter(
            ChatHistory.role == 'user'
        ).order_by(desc(ChatHistory.created_at))
        
        if session_ids:
            query = query.filter(ChatHistory.session_id.in_(session_ids))
        
        user_messages = query.offset(offset).limit(limit).all()
        
        dataset_items = db.query(EvaluationDataset).all()
        
        results = []
        for msg in user_messages:
            session_messages = db.query(ChatHistory).filter(
                ChatHistory.session_id == msg.session_id
            ).order_by(ChatHistory.created_at).all()
            
            user_msg = None
            assistant_msg = None
            for i, m in enumerate(session_messages):
                if m.id == msg.id:
                    user_msg = m
                    if i + 1 < len(session_messages) and session_messages[i + 1].role == 'assistant':
                        assistant_msg = session_messages[i + 1]
                    break
            
            if not user_msg or not assistant_msg:
                continue
            
            try:
                contexts = await self._get_contexts_for_query(user_msg.content)
                
                ground_truth = self._match_ground_truth(user_msg.content, dataset_items)
                
                scores = await self.evaluate_single(
                    query=user_msg.content,
                    answer=assistant_msg.content,
                    contexts=contexts,
                    ground_truth=ground_truth
                )
                
                results.append({
                    'session_id': msg.session_id,
                    'query': user_msg.content,
                    'answer': assistant_msg.content,
                    'contexts': contexts,
                    'ground_truth': ground_truth,
                    'scores': scores,
                    'created_at': user_msg.created_at.isoformat()
                })
            except Exception as e:
                logger.error(f"Evaluation failed for message {msg.id}: {e}")
                continue
        
        return results

    async def _get_contexts_for_query(self, query: str, top_k: int = 3) -> List[str]:
        try:
            results = await hybrid_search_service.search(
                query=query,
                top_k=top_k,
                use_rerank=True
            )
            return [r.get('content', '') for r in results if r.get('content')]
        except Exception as e:
            logger.error(f"Failed to get contexts: {e}")
            return []

    async def _builtin_batch_evaluate(
        self,
        samples: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        logger.info("=" * 50)
        logger.info("正在使用内置评估框架...")
        logger.info(f"评估样本数量: {len(samples)}")
        logger.info("=" * 50)
        
        all_scores = {
            'faithfulness': [],
            'answer_relevancy': [],
            'context_precision': []
        }
        
        for i, sample in enumerate(samples):
            logger.info(f"正在评估第 {i+1}/{len(samples)} 条样本...")
            scores = await self.evaluate_single(
                query=sample.get('query', ''),
                answer=sample.get('answer', ''),
                contexts=sample.get('contexts', []),
                ground_truth=sample.get('ground_truth')
            )
            logger.info(f"第 {i+1} 条样本评估结果: faithfulness={scores.get('faithfulness', 'N/A'):.4f}, answer_relevancy={scores.get('answer_relevancy', 'N/A'):.4f}")
            for key in all_scores:
                if key in scores:
                    all_scores[key].append(scores[key])
        
        avg_scores = {}
        for key, values in all_scores.items():
            if values:
                avg_scores[key] = sum(values) / len(values)
        
        logger.info("=" * 50)
        logger.info("内置评估完成!")
        logger.info(f"平均分数: {avg_scores}")
        logger.info("=" * 50)
        
        return {
            'framework': 'builtin',
            'metrics': avg_scores,
            'sample_count': len(samples)
        }

    def get_evaluation_summary(
        self,
        results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        if not results:
            return {
                'total_evaluations': 0,
                'average_scores': {},
                'score_distribution': {}
            }
        
        all_scores = {
            'faithfulness': [],
            'answer_relevancy': [],
            'context_precision': [],
            'overall_score': []
        }
        
        for result in results:
            scores = result.get('scores', {})
            for key in all_scores:
                if key in scores:
                    sanitized_score = self._sanitize_score_value(scores[key])
                    if sanitized_score is not None:
                        all_scores[key].append(sanitized_score)
        
        avg_scores = {}
        for key, values in all_scores.items():
            if values:
                avg_scores[key] = round(sum(values) / len(values), 4)
        
        distribution = {}
        for key, values in all_scores.items():
            if values:
                distribution[key] = {
                    'excellent': len([v for v in values if v >= 0.8]),
                    'good': len([v for v in values if 0.6 <= v < 0.8]),
                    'fair': len([v for v in values if 0.4 <= v < 0.6]),
                    'poor': len([v for v in values if v < 0.4])
                }
        
        return {
            'total_evaluations': len(results),
            'average_scores': avg_scores,
            'score_distribution': distribution
        }


evaluation_service = EvaluationService()
