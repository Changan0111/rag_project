from sentence_transformers import CrossEncoder
from typing import List, Optional
from app.core.config import settings
import logging
import os
import torch
from functools import lru_cache

logger = logging.getLogger(__name__)


class RerankService:
    def __init__(self, model_name: str = None):
        self.model_name = model_name or settings.RERANK_MODEL
        self.model: Optional[CrossEncoder] = None
        self._enabled = settings.RERANK_ENABLED
        self.device = None
        self._model_loaded = False

    def _get_device(self):
        # ✅ 优先检查强制CPU配置（不占用GPU显存，留给LLM）
        if settings.FORCE_RERANK_CPU:
            logger.info("FORCE_RERANK_CPU=True, using CPU for rerank inference (saving GPU memory for LLM)")
            return "cpu"
        
        if settings.USE_GPU and torch.cuda.is_available():
            device = "cuda"
            gpu_count = torch.cuda.device_count()
            
            if gpu_count > 1:
                for i in range(gpu_count):
                    gpu_name = torch.cuda.get_device_name(i)
                    if "NVIDIA" in gpu_name:
                        device = f"cuda:{i}"
                        logger.info(f"NVIDIA GPU found: {gpu_name} (device {i})")
                        break
            else:
                gpu_name = torch.cuda.get_device_name(0)
                logger.info(f"GPU available: {gpu_name}")
        elif settings.USE_GPU and torch.backends.mps.is_available():
            device = "mps"
            logger.info("Apple Silicon GPU (MPS) available")
        else:
            device = "cpu"
            logger.info("Using CPU for rerank inference")
        return device

    def load_model(self):
        if self._model_loaded:
            return
            
        if not self._enabled:
            logger.info("Reranking is disabled")
            return
        
        cache_dir = os.path.join(os.path.dirname(__file__), "..", "..", "models")
        os.makedirs(cache_dir, exist_ok=True)
        
        os.environ['SENTENCE_TRANSFORMERS_HOME'] = cache_dir
        
        self.device = self._get_device()
        
        logger.info(f"Loading rerank model: {self.model_name} on {self.device}")
        self.model = CrossEncoder(
            self.model_name,
            max_length=512,  # 限制最大长度以提升性能
            device=self.device
        )
        self._model_loaded = True
        logger.info(f"Rerank model loaded successfully on {self.device}")

    def preload(self):
        if self._enabled and not self._model_loaded:
            self.load_model()

    def is_enabled(self) -> bool:
        return self._enabled

    def rerank(
        self,
        query: str,
        documents: List[dict],
        top_k: int = 5,
        content_key: str = "content"
    ) -> List[dict]:
        if not documents:
            return []
        
        if not self._enabled:
            return documents[:top_k]
        
        if self.model is None:
            self.load_model()

        pairs = [[query, doc[content_key]] for doc in documents]
        
        with torch.no_grad():  # 禁用梯度计算，节省内存和加速推理
            scores = self.model.predict(pairs)
        
        for i, doc in enumerate(documents):
            doc["rerank_score"] = float(scores[i])
        
        sorted_docs = sorted(documents, key=lambda x: x["rerank_score"], reverse=True)[:top_k]
        
        for i, doc in enumerate(sorted_docs):
            doc["final_rank"] = i + 1
        
        logger.info(f"Reranked {len(documents)} documents, returned top {top_k}")
        
        return sorted_docs

    def rerank_with_scores(
        self,
        query: str,
        documents: List[dict],
        top_k: int = 5,
        content_key: str = "content",
        return_all: bool = False
    ) -> List[dict]:
        if not documents:
            return []
        
        if not self._enabled:
            return documents[:top_k]
        
        if self.model is None:
            self.load_model()

        pairs = [[query, doc[content_key]] for doc in documents]
        
        with torch.no_grad():
            scores = self.model.predict(pairs)
        
        for i, doc in enumerate(documents):
            doc["rerank_score"] = float(scores[i])
        
        sorted_docs = sorted(documents, key=lambda x: x["rerank_score"], reverse=True)
        
        if return_all:
            for i, doc in enumerate(sorted_docs):
                doc["final_rank"] = i + 1
            return sorted_docs
        
        result = sorted_docs[:top_k]
        for i, doc in enumerate(result):
            doc["final_rank"] = i + 1
        
        logger.info(f"Reranked {len(documents)} documents, returned top {top_k}")
        
        return result


rerank_service = RerankService()
