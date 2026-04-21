from sentence_transformers import SentenceTransformer
from typing import List, Optional
from app.core.config import settings
import logging
import os
import torch
import warnings
warnings.filterwarnings("ignore", message="`resume_download` is deprecated")

logger = logging.getLogger(__name__)


class EmbeddingService:
    def __init__(self):
        self.model_name = settings.EMBEDDING_MODEL
        self.dimension = settings.EMBEDDING_DIMENSION
        self.model: Optional[SentenceTransformer] = None
        self.device = None
        self.max_tokens = settings.EMBEDDING_MAX_TOKENS
        self.batch_size = settings.EMBEDDING_BATCH_SIZE

    def _get_device(self):
        # ✅ 优先检查强制CPU配置（不占用GPU显存，留给LLM）
        if settings.FORCE_EMBEDDING_CPU:
            logger.info("FORCE_EMBEDDING_CPU=True, using CPU for embedding inference (saving GPU memory for LLM)")
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
            logger.info("Using CPU for inference")
        return device

    def load_model(self):
        if self.model is None:
            cache_dir = os.path.join(os.path.dirname(__file__), "..", "..", "models")
            os.makedirs(cache_dir, exist_ok=True)
            
            self.device = self._get_device()
            
            logger.info(f"Loading embedding model: {self.model_name} on {self.device}")
            self.model = SentenceTransformer(
                self.model_name,
                cache_folder=cache_dir,
                device=self.device
            )
            
            self.model.max_seq_length = self.max_tokens
            
            logger.info(
                f"Embedding model loaded: dimension={self.dimension}, "
                f"device={self.device}, max_seq_length={self.max_tokens}, "
                f"batch_size={self.batch_size}"
            )

    def _truncate_text(self, text: str) -> str:
        if len(text) <= self.max_tokens * 2:
            return text
        
        truncated = text[:self.max_tokens * 2]
        return truncated

    def encode(self, texts: List[str]) -> List[List[float]]:
        if self.model is None:
            self.load_model()

        truncated_texts = [self._truncate_text(text) for text in texts]

        embeddings = self.model.encode(
            truncated_texts,
            normalize_embeddings=True,
            show_progress_bar=False,
            batch_size=self.batch_size,
            convert_to_numpy=True
        )
        return embeddings.tolist()

    def encode_batch(self, texts: List[str], batch_size: Optional[int] = None) -> List[List[float]]:
        if self.model is None:
            self.load_model()

        actual_batch_size = batch_size or self.batch_size
        truncated_texts = [self._truncate_text(text) for text in texts]

        embeddings = self.model.encode(
            truncated_texts,
            normalize_embeddings=True,
            show_progress_bar=len(texts) > 100,
            batch_size=actual_batch_size,
            convert_to_numpy=True
        )
        return embeddings.tolist()

    def encode_single(self, text: str) -> List[float]:
        return self.encode([text])[0]


embedding_service = EmbeddingService()
