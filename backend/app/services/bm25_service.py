import jieba
import math
import logging
import pickle
import os
from typing import List, Dict, Optional, Set
from collections import defaultdict
import re
from datetime import datetime

logger = logging.getLogger(__name__)

BM25_INDEX_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "data", "bm25_index.pkl")


class BM25Service:
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.documents: Dict[int, dict] = {}
        self.doc_count: int = 0
        self.avgdl: float = 0.0
        self.doc_freqs: Dict[str, int] = defaultdict(int)
        self.doc_len: Dict[int, int] = {}
        self.idf: Dict[str, float] = {}
        self._initialized: bool = False
        self._index_file = BM25_INDEX_FILE

        jieba.initialize()
        logger.info("BM25Service initialized with jieba tokenizer")

        if self.has_saved_index():
            loaded = self.load_index()
            if loaded:
                logger.info(f"BM25Service auto-loaded index from disk ({self.doc_count} docs)")
            else:
                logger.warning(f"BM25Service auto-load failed, index file exists at {self._index_file}, will need manual rebuild")

    def _tokenize(self, text: str) -> List[str]:
        text = re.sub(r'[^\w\s\u4e00-\u9fff]', ' ', text)
        tokens = jieba.lcut(text.lower())
        tokens = [t.strip() for t in tokens if t.strip() and len(t.strip()) > 1]
        return tokens

    def add_document(self, doc_id: int, content: str, category: str = None, chunk_index: int = 0):
        internal_id = doc_id * 10000 + chunk_index
        tokens = self._tokenize(content)
        self.documents[internal_id] = {
            "doc_id": doc_id,
            "internal_id": internal_id,
            "chunk_index": chunk_index,
            "content": content,
            "category": category,
            "tokens": tokens,
            "tf": defaultdict(int)
        }

        for token in tokens:
            self.documents[internal_id]["tf"][token] += 1

        self.doc_len[internal_id] = len(tokens)
        self.doc_count += 1

        unique_tokens = set(tokens)
        for token in unique_tokens:
            self.doc_freqs[token] += 1

        self._initialized = False
        logger.debug(f"Added document {doc_id} to BM25 index")

    def remove_document(self, doc_id: int):
        keys_to_remove = [
            k for k, v in self.documents.items()
            if v.get("doc_id") == doc_id
        ]
        for internal_id in keys_to_remove:
            doc = self.documents[internal_id]
            tokens = set(doc["tokens"])

            for token in tokens:
                if self.doc_freqs[token] > 0:
                    self.doc_freqs[token] -= 1

            del self.documents[internal_id]
            if internal_id in self.doc_len:
                del self.doc_len[internal_id]

        self.doc_count -= len(keys_to_remove)
        self._initialized = False
        logger.debug(f"Removed document {doc_id} from BM25 index")

    def _calculate_idf(self):
        self.idf = {}
        for token, df in self.doc_freqs.items():
            if df > 0:
                self.idf[token] = math.log((self.doc_count - df + 0.5) / (df + 0.5) + 1)
            else:
                self.idf[token] = 0

    def _calculate_avgdl(self):
        if self.doc_count > 0:
            self.avgdl = sum(self.doc_len.values()) / self.doc_count
        else:
            self.avgdl = 0

    def _ensure_initialized(self):
        if not self._initialized:
            if self.doc_count == 0 and self.has_saved_index():
                logger.info("BM25 index empty but saved file exists, attempting lazy load")
                if self.load_index():
                    return
                logger.warning("BM25 lazy load failed, will calculate from in-memory state")
            self._calculate_idf()
            self._calculate_avgdl()
            self._initialized = True

    def search(
        self,
        query: str,
        top_k: int = 5,
        category: Optional[str] = None
    ) -> List[dict]:
        self._ensure_initialized()

        if self.doc_count == 0:
            return []

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        scores: Dict[int, float] = defaultdict(float)

        for token in query_tokens:
            if token not in self.idf:
                continue

            for doc_id, doc in self.documents.items():
                if category and doc.get("category") != category:
                    continue

                tf = doc["tf"].get(token, 0)
                if tf == 0:
                    continue

                doc_len = self.doc_len.get(doc_id, 0)
                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (1 - self.b + self.b * doc_len / self.avgdl) if self.avgdl > 0 else tf + self.k1

                scores[doc_id] += self.idf[token] * numerator / denominator

        sorted_docs = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

        results = []
        for internal_id, score in sorted_docs:
            doc = self.documents.get(internal_id)
            if doc:
                results.append({
                    "doc_id": doc["doc_id"],
                    "chunk_index": doc.get("chunk_index", 0),
                    "content": doc["content"],
                    "category": doc.get("category"),
                    "score": score
                })

        return results

    def get_stats(self) -> dict:
        return {
            "doc_count": self.doc_count,
            "avg_doc_len": round(self.avgdl, 2),
            "vocab_size": len(self.doc_freqs),
            "initialized": self._initialized
        }

    def clear(self):
        self.documents.clear()
        self.doc_count = 0
        self.avgdl = 0.0
        self.doc_freqs.clear()
        self.doc_len.clear()
        self.idf.clear()
        self._initialized = False
        logger.info("BM25 index cleared")

    def save_index(self) -> bool:
        try:
            self._ensure_initialized()

            index_dir = os.path.dirname(self._index_file)
            if not os.path.exists(index_dir):
                os.makedirs(index_dir)
            
            index_data = {
                "documents": self.documents,
                "doc_count": self.doc_count,
                "avgdl": self.avgdl,
                "doc_freqs": dict(self.doc_freqs),
                "doc_len": self.doc_len,
                "idf": self.idf,
                "k1": self.k1,
                "b": self.b,
                "saved_at": datetime.now().isoformat()
            }
            
            with open(self._index_file, "wb") as f:
                pickle.dump(index_data, f)
            
            logger.info(f"BM25 index saved to {self._index_file}, docs={self.doc_count}")
            return True
        except Exception as e:
            logger.error(f"Failed to save BM25 index: {e}")
            return False

    def load_index(self) -> bool:
        try:
            if not os.path.exists(self._index_file):
                logger.info(f"BM25 index file not found: {self._index_file}")
                return False

            with open(self._index_file, "rb") as f:
                index_data = pickle.load(f)

            if index_data.get("k1") != self.k1 or index_data.get("b") != self.b:
                logger.warning(
                    f"BM25 parameters mismatch: saved(k1={index_data.get('k1')}, b={index_data.get('b')}) "
                    f"vs current(k1={self.k1}, b={self.b}), will rebuild index"
                )
                return False

            self.documents = index_data.get("documents", {})
            self.doc_count = index_data.get("doc_count", 0)
            self.avgdl = index_data.get("avgdl", 0.0)
            self.doc_freqs = defaultdict(int, index_data.get("doc_freqs", {}))
            self.doc_len = index_data.get("doc_len", {})
            self.idf = index_data.get("idf", {})
            self._initialized = True

            if self.doc_count > 0 and (not self.idf or self.avgdl <= 0):
                logger.warning(
                    f"Loaded BM25 index has inconsistent state: "
                    f"docs={self.doc_count}, idf_count={len(self.idf)}, avgdl={self.avgdl}. "
                    f"Recalculating IDF and avgdl from in-memory data."
                )
                self._calculate_idf()
                self._calculate_avgdl()
                logger.info(f"Recalculated: idf_count={len(self.idf)}, avgdl={round(self.avgdl, 2)}")

            saved_at = index_data.get("saved_at", "unknown")
            logger.info(
                f"BM25 index loaded from {self._index_file}, "
                f"docs={self.doc_count}, vocab={len(self.doc_freqs)}, "
                f"avgdl={round(self.avgdl, 2)}, saved_at={saved_at}"
            )
            return True
        except pickle.UnpicklingError as e:
            logger.error(f"BM25 index pickle format error (possibly corrupted or version mismatch): {e}")
            return False
        except EOFError as e:
            logger.error(f"BM25 index file is empty or truncated: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to load BM25 index: {type(e).__name__}: {e}")
            return False

    def has_saved_index(self) -> bool:
        return os.path.exists(self._index_file)

    def get_index_info(self) -> dict:
        info = {
            "has_saved_index": self.has_saved_index(),
            "current_doc_count": self.doc_count,
            "index_file": self._index_file
        }
        if self.has_saved_index():
            try:
                stat = os.stat(self._index_file)
                info["file_size_kb"] = round(stat.st_size / 1024, 2)
                info["file_modified"] = datetime.fromtimestamp(stat.st_mtime).isoformat()
            except Exception:
                pass
        return info


bm25_service = BM25Service()
