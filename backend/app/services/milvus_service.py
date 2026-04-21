from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility
from typing import List, Optional
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class MilvusService:
    def __init__(self):
        self.collection_name = settings.COLLECTION_NAME
        self.dimension = settings.EMBEDDING_DIMENSION
        self.collection: Optional[Collection] = None
        self._connected = False

    def connect(self):
        try:
            connections.connect(
                alias="default",
                host=settings.MILVUS_HOST,
                port=settings.MILVUS_PORT
            )
            self._connected = True
            logger.info(f"Connected to Milvus at {settings.MILVUS_HOST}:{settings.MILVUS_PORT}")
        except Exception as e:
            logger.error(f"Failed to connect to Milvus: {e}")
            raise

    def _get_index_info(self) -> Optional[dict]:
        if self.collection is None:
            return None
        try:
            indexes = self.collection.indexes
            for index in indexes:
                if index.field_name == "embedding":
                    return {
                        "field_name": index.field_name,
                        "index_name": index.index_name,
                        "params": index.params
                    }
        except Exception as e:
            logger.warning(f"Failed to get index info: {e}")
        return None

    def _needs_index_upgrade(self) -> bool:
        index_info = self._get_index_info()
        if index_info is None:
            return True
        current_index_type = index_info.get("params", {}).get("index_type", "")
        if current_index_type != "HNSW":
            logger.info(f"Current index type: {current_index_type}, upgrading to HNSW")
            return True
        return False

    def _drop_and_recreate_collection(self):
        if utility.has_collection(self.collection_name):
            logger.info(f"Dropping existing collection {self.collection_name} for HNSW upgrade")
            utility.drop_collection(self.collection_name)
        self._create_hnsw_collection()

    def _create_hnsw_collection(self):
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="doc_id", dtype=DataType.INT64),
            FieldSchema(name="chunk_id", dtype=DataType.INT64),
            FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=2000),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.dimension),
            FieldSchema(name="category", dtype=DataType.VARCHAR, max_length=50)
        ]

        schema = CollectionSchema(fields=fields, description="Knowledge vectors for RAG with HNSW index (chunked)")
        self.collection = Collection(name=self.collection_name, schema=schema)

        index_params = {
            "metric_type": "COSINE",
            "index_type": "HNSW",
            "params": {
                "M": settings.HNSW_M,
                "efConstruction": settings.HNSW_EF_CONSTRUCTION
            }
        }
        self.collection.create_index(field_name="embedding", index_params=index_params)
        logger.info(f"Created collection {self.collection_name} with HNSW index (M={settings.HNSW_M}, efConstruction={settings.HNSW_EF_CONSTRUCTION})")

    def create_collection(self):
        if not self._connected:
            self.connect()

        if utility.has_collection(self.collection_name):
            logger.info(f"Collection {self.collection_name} already exists")
            self.collection = Collection(self.collection_name)
            
            if self._needs_index_upgrade():
                logger.info("Index upgrade needed, will recreate collection on next sync")
            return

        self._create_hnsw_collection()

    def _needs_schema_update(self) -> bool:
        if self.collection is None:
            return True
        try:
            existing_fields = {f.name for f in self.collection.schema.fields}
            expected_fields = {"id", "doc_id", "chunk_id", "content", "embedding", "category"}
            if existing_fields != expected_fields:
                logger.info(f"Schema mismatch: existing={existing_fields}, expected={expected_fields}")
                return True
        except Exception as e:
            logger.warning(f"Failed to check schema: {e}")
            return True
        return False

    def ensure_hnsw_index(self) -> bool:
        if not self._connected:
            self.connect()

        if utility.has_collection(self.collection_name):
            self.collection = Collection(self.collection_name)
            needs_recreate = False
            if self._needs_index_upgrade():
                needs_recreate = True
            if self._needs_schema_update():
                needs_recreate = True
            if needs_recreate:
                self._drop_and_recreate_collection()
                return True
        else:
            self._create_hnsw_collection()
            return True
        return False

    def insert_vectors(
        self,
        doc_ids: List[int],
        contents: List[str],
        embeddings: List[List[float]],
        categories: List[str],
        chunk_ids: List[int] = None
    ) -> int:
        if self.collection is None:
            self.create_collection()

        if chunk_ids is None:
            chunk_ids = [0] * len(doc_ids)

        entities = [
            doc_ids,
            chunk_ids,
            contents,
            embeddings,
            categories
        ]

        insert_result = self.collection.insert(entities)
        self.collection.flush()
        logger.info(f"Inserted {len(doc_ids)} vectors into {self.collection_name}")
        return insert_result.insert_count

    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        category: Optional[str] = None
    ) -> List[dict]:
        if self.collection is None:
            self.create_collection()

        self.collection.load()

        search_params = {
            "metric_type": "COSINE",
            "params": {"ef": settings.HNSW_EF_SEARCH}
        }

        filter_expr = None
        if category:
            filter_expr = f'category == "{category}"'

        results = self.collection.search(
            data=[query_embedding],
            anns_field="embedding",
            param=search_params,
            limit=top_k,
            expr=filter_expr,
            output_fields=["doc_id", "chunk_id", "content", "category"]
        )

        search_results = []
        for hits in results:
            for hit in hits:
                search_results.append({
                    "doc_id": hit.entity.get("doc_id"),
                    "chunk_id": hit.entity.get("chunk_id") or 0,
                    "content": hit.entity.get("content"),
                    "category": hit.entity.get("category"),
                    "score": hit.score
                })

        return search_results

    def delete_by_doc_id(self, doc_id: int):
        if self.collection is None:
            self.create_collection()

        try:
            self.collection.load()
        except Exception as e:
            logger.warning(f"Collection load failed (may be empty): {e}")

        expr = f'doc_id == {doc_id}'
        self.collection.delete(expr)
        self.collection.flush()
        logger.info(f"Deleted vectors with doc_id {doc_id}")

    def get_collection_stats(self) -> dict:
        if self.collection is None:
            self.create_collection()

        self.collection.flush()
        stats = self.collection.num_entities
        index_info = self._get_index_info()
        
        return {
            "collection_name": self.collection_name,
            "num_entities": stats,
            "index_type": index_info.get("params", {}).get("index_type", "unknown") if index_info else "none",
            "index_params": index_info.get("params", {}) if index_info else {}
        }


milvus_service = MilvusService()
