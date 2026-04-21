import hashlib
import logging
from typing import Optional, List
import numpy as np
from app.services.redis_service import redis_service
from app.services.embedding_service import embedding_service
from app.core.config import settings

logger = logging.getLogger(__name__)


class SemanticCacheService:
    CACHE_PREFIX = "rag:cache:"
    EMBEDDING_PREFIX = "rag:embedding:"

    def __init__(self):
        self._similarity_threshold = settings.CACHE_SIMILARITY_THRESHOLD
        self._ttl = settings.CACHE_TTL

    def _compute_cache_key(self, query: str) -> str:
        query_hash = hashlib.md5(query.encode()).hexdigest()
        return f"{self.CACHE_PREFIX}{query_hash}"

    def _compute_embedding_key(self, query: str) -> str:
        query_hash = hashlib.md5(query.encode()).hexdigest()
        return f"{self.EMBEDDING_PREFIX}{query_hash}"

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(dot_product / (norm1 * norm2))

    def get(self, query: str) -> Optional[dict]:
        if not redis_service.is_enabled():
            logger.warning("Redis not enabled, skip cache get")
            return None

        cache_key = self._compute_cache_key(query)

        logger.info(f"Cache lookup: query='{query[:50]}...', cache_key={cache_key}")

        cached = redis_service.get(cache_key)
        if cached:
            logger.info(f"Cache hit (exact): {query[:50]}...")
            return cached

        try:
            all_keys = redis_service._client.keys(f"{self.CACHE_PREFIX}*")
            logger.info(f"Found {len(all_keys)} cache keys for semantic search")
            if not all_keys:
                logger.info(f"Cache miss: no cache keys found")
                return None

            query_embedding = embedding_service.encode_single(query)

            best_match = None
            best_similarity = 0.0

            for key in all_keys[:50]:
                if key == cache_key:
                    continue

                cached_embedding = redis_service.get(key.replace(self.CACHE_PREFIX, self.EMBEDDING_PREFIX))
                if not cached_embedding:
                    continue

                similarity = self._cosine_similarity(query_embedding, cached_embedding)
                if similarity > best_similarity and similarity >= self._similarity_threshold:
                    best_similarity = similarity
                    best_match = key

            if best_match:
                cached_result = redis_service.get(best_match)
                if cached_result:
                    logger.info(f"Cache hit (semantic): {query[:50]}... (similarity: {best_similarity:.3f})")
                    return cached_result

        except Exception as e:
            logger.error(f"Semantic cache search error: {e}")

        logger.info(f"Cache miss: {query[:50]}...")
        return None

    def set(self, query: str, result: dict):
        if not redis_service.is_enabled():
            logger.warning("Redis not enabled, skip caching")
            return

        cache_key = self._compute_cache_key(query)
        embedding_key = self._compute_embedding_key(query)

        query_embedding = embedding_service.encode_single(query)

        if hasattr(query_embedding, 'tolist'):
            embedding_list = query_embedding.tolist()
        else:
            embedding_list = list(query_embedding) if not isinstance(query_embedding, list) else query_embedding

        cache_success = redis_service.set(cache_key, result, self._ttl)
        embedding_success = redis_service.set(embedding_key, embedding_list, self._ttl)
        
        logger.info(f"Cache set: query='{query[:50]}...', key={cache_key}, cache_success={cache_success}, embedding_success={embedding_success}")

    def delete(self, query: str):
        if not redis_service.is_enabled():
            return

        cache_key = self._compute_cache_key(query)
        embedding_key = self._compute_embedding_key(query)

        redis_service.delete(cache_key)
        redis_service.delete(embedding_key)

    def clear_all(self):
        if not redis_service.is_enabled():
            return

        try:
            cache_keys = redis_service._client.keys(f"{self.CACHE_PREFIX}*")
            embedding_keys = redis_service._client.keys(f"{self.EMBEDDING_PREFIX}*")
            
            all_keys = cache_keys + embedding_keys
            if all_keys:
                redis_service._client.delete(*all_keys)
                logger.info(f"Cleared {len(all_keys)} cache entries")
        except Exception as e:
            logger.error(f"Clear cache error: {e}")

    def get_stats(self) -> dict:
        if not redis_service.is_enabled():
            return {"enabled": False}

        try:
            cache_keys = redis_service._client.keys(f"{self.CACHE_PREFIX}*")
            embedding_keys = redis_service._client.keys(f"{self.EMBEDDING_PREFIX}*")
            
            return {
                "enabled": True,
                "cache_entries": len(cache_keys),
                "embedding_entries": len(embedding_keys),
                "similarity_threshold": self._similarity_threshold,
                "ttl": self._ttl
            }
        except Exception as e:
            return {"enabled": False, "error": str(e)}

    def get_cache_list(self, page: int = 1, page_size: int = 20, keyword: str = None) -> dict:
        if not redis_service.is_enabled():
            return {"enabled": False, "items": [], "total": 0}

        try:
            cache_keys = redis_service._client.keys(f"{self.CACHE_PREFIX}*")
            total = len(cache_keys)
            logger.info(f"Found {total} cache keys with prefix {self.CACHE_PREFIX}")
            
            items = []
            for key in cache_keys:
                try:
                    cached_data = redis_service.get(key)
                    ttl = redis_service.get_key_ttl(key)
                    logger.debug(f"Key: {key}, TTL: {ttl}, Data: {cached_data is not None}")
                    
                    if cached_data:
                        query_preview = cached_data.get("query", "")[:100] if cached_data.get("query") else ""
                        answer_preview = cached_data.get("answer", "")[:100] if cached_data.get("answer") else ""
                        
                        if keyword:
                            if keyword.lower() not in query_preview.lower() and keyword.lower() not in answer_preview.lower():
                                continue
                        
                        items.append({
                            "key": key,
                            "query": cached_data.get("query", ""),
                            "query_preview": query_preview,
                            "answer_preview": answer_preview,
                            "ttl": ttl,
                            "created_at": cached_data.get("created_at", "")
                        })
                    else:
                        logger.warning(f"No data found for key: {key}")
                except Exception as e:
                    logger.error(f"Error reading cache key {key}: {e}")
                    continue

            items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            
            start = (page - 1) * page_size
            end = start + page_size
            paginated_items = items[start:end]
            
            logger.info(f"Returning {len(paginated_items)} items out of {len(items)} total")
            
            return {
                "enabled": True,
                "items": paginated_items,
                "total": len(items),
                "page": page,
                "page_size": page_size
            }
        except Exception as e:
            logger.error(f"Get cache list error: {e}")
            return {"enabled": False, "items": [], "total": 0, "error": str(e)}

    def get_cache_detail(self, key: str) -> dict:
        if not redis_service.is_enabled():
            return {"enabled": False}

        try:
            cached_data = redis_service.get(key)
            if not cached_data:
                return {"enabled": True, "found": False}

            ttl = redis_service.get_key_ttl(key)
            
            return {
                "enabled": True,
                "found": True,
                "key": key,
                "query": cached_data.get("query", ""),
                "answer": cached_data.get("answer", ""),
                "ttl": ttl,
                "created_at": cached_data.get("created_at", "")
            }
        except Exception as e:
            logger.error(f"Get cache detail error: {e}")
            return {"enabled": False, "error": str(e)}

    def delete_cache_by_key(self, key: str) -> bool:
        if not redis_service.is_enabled():
            return False

        try:
            if key.startswith(self.CACHE_PREFIX):
                embedding_key = key.replace(self.CACHE_PREFIX, self.EMBEDDING_PREFIX)
                redis_service.delete(key)
                redis_service.delete(embedding_key)
                return True
            elif key.startswith(self.EMBEDDING_PREFIX):
                cache_key = key.replace(self.EMBEDDING_PREFIX, self.CACHE_PREFIX)
                redis_service.delete(key)
                redis_service.delete(cache_key)
                return True
            return False
        except Exception as e:
            logger.error(f"Delete cache by key error: {e}")
            return False

    def delete_cache_by_keys(self, keys: list) -> int:
        if not redis_service.is_enabled() or not keys:
            return 0

        try:
            all_keys_to_delete = set()
            
            for key in keys:
                if key.startswith(self.CACHE_PREFIX):
                    all_keys_to_delete.add(key)
                    embedding_key = key.replace(self.CACHE_PREFIX, self.EMBEDDING_PREFIX)
                    all_keys_to_delete.add(embedding_key)
                elif key.startswith(self.EMBEDDING_PREFIX):
                    all_keys_to_delete.add(key)
                    cache_key = key.replace(self.EMBEDDING_PREFIX, self.CACHE_PREFIX)
                    all_keys_to_delete.add(cache_key)
                else:
                    all_keys_to_delete.add(key)
            
            if all_keys_to_delete:
                keys_list = list(all_keys_to_delete)
                deleted = redis_service.delete_keys(keys_list)
                logger.info(f"Batch deleted {deleted} keys from {len(keys)} input keys")
                return deleted
            
            return 0
        except Exception as e:
            logger.error(f"Batch delete cache error: {e}")
            return 0


semantic_cache_service = SemanticCacheService()
