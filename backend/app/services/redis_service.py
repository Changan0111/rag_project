import redis
import json
import logging
from typing import Optional, Any
from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisService:
    def __init__(self):
        self._client = None
        self._enabled = settings.CACHE_ENABLED

    def connect(self):
        if not self._enabled:
            logger.info("Cache is disabled")
            return

        try:
            self._client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            self._client.ping()
            logger.info(f"Redis connected: {settings.REDIS_HOST}:{settings.REDIS_PORT}")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}, cache disabled")
            self._enabled = False
            self._client = None

    def is_enabled(self) -> bool:
        return self._enabled and self._client is not None

    def get(self, key: str) -> Optional[Any]:
        if not self.is_enabled():
            return None

        try:
            value = self._client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None

    def set(self, key: str, value: Any, ttl: int = None):
        if not self.is_enabled():
            logger.warning("Redis not enabled, cannot set key")
            return False

        try:
            ttl = ttl or settings.CACHE_TTL
            json_value = json.dumps(value, ensure_ascii=False)
            self._client.setex(key, ttl, json_value)
            logger.info(f"Redis SET success: key={key}, ttl={ttl}, value_len={len(json_value)}")
            return True
        except Exception as e:
            logger.error(f"Redis set error: {e}")
            return False

    def delete(self, key: str):
        if not self.is_enabled():
            return False

        try:
            self._client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
            return False

    def exists(self, key: str) -> bool:
        if not self.is_enabled():
            return False

        try:
            return self._client.exists(key) > 0
        except Exception as e:
            logger.error(f"Redis exists error: {e}")
            return False

    def get_stats(self) -> dict:
        if not self.is_enabled():
            return {"enabled": False}

        try:
            clients_info = self._client.info("clients")
            stats_info = self._client.info("stats")
            return {
                "enabled": True,
                "connected_clients": clients_info.get("connected_clients", 0),
                "total_commands_processed": stats_info.get("total_commands_processed", 0),
                "keyspace_hits": stats_info.get("keyspace_hits", 0),
                "keyspace_misses": stats_info.get("keyspace_misses", 0),
            }
        except Exception as e:
            logger.error(f"Redis get_stats error: {e}")
            return {"enabled": False, "error": str(e)}

    def get_keys_by_pattern(self, pattern: str) -> list:
        if not self.is_enabled():
            return []
        try:
            return self._client.keys(pattern)
        except Exception as e:
            logger.error(f"Redis get_keys_by_pattern error: {e}")
            return []

    def get_key_ttl(self, key: str) -> int:
        if not self.is_enabled():
            return -1
        try:
            return self._client.ttl(key)
        except Exception as e:
            logger.error(f"Redis get_key_ttl error: {e}")
            return -1

    def get_key_type(self, key: str) -> str:
        if not self.is_enabled():
            return "none"
        try:
            key_type = self._client.type(key)
            return key_type
        except Exception as e:
            logger.error(f"Redis get_key_type error: {e}")
            return "none"

    def delete_keys(self, keys: list) -> int:
        if not self.is_enabled() or not keys:
            return 0
        try:
            return self._client.delete(*keys)
        except Exception as e:
            logger.error(f"Redis delete_keys error: {e}")
            return 0

    def get_memory_usage(self) -> dict:
        if not self.is_enabled():
            return {"enabled": False}
        try:
            info = self._client.info("memory")
            return {
                "enabled": True,
                "used_memory": info.get("used_memory", 0),
                "used_memory_human": info.get("used_memory_human", "0B"),
                "used_memory_peak": info.get("used_memory_peak", 0),
                "used_memory_peak_human": info.get("used_memory_peak_human", "0B"),
            }
        except Exception as e:
            logger.error(f"Redis get_memory_usage error: {e}")
            return {"enabled": False, "error": str(e)}

    def get_db_size(self) -> int:
        if not self.is_enabled():
            return 0
        try:
            return self._client.dbsize()
        except Exception as e:
            logger.error(f"Redis get_db_size error: {e}")
            return 0

    def close(self):
        if self._client:
            self._client.close()
            logger.info("Redis connection closed")


redis_service = RedisService()
