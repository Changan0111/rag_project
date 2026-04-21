import logging
import threading
from typing import Optional
from datetime import datetime
from sqlalchemy import event
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class KnowledgeSyncService:
    def __init__(self):
        self._pending_updates: dict = {}
        self._lock = threading.Lock()
        self._initialized = False
        self._db_session_factory = None

    def init_services(self):
        if self._initialized:
            return

        from app.services.embedding_service import embedding_service
        from app.services.milvus_service import milvus_service
        from app.services.bm25_service import bm25_service
        from app.core.database import SessionLocal

        self.embedding_service = embedding_service
        self.milvus_service = milvus_service
        self.bm25_service = bm25_service
        self._db_session_factory = SessionLocal
        self._initialized = True
        logger.info("KnowledgeSyncService initialized")

    def _log_sync(self, doc_id: int, action: str, status: str, error_message: str = None):
        try:
            from app.models import KnowledgeSyncLog
            
            db = self._db_session_factory()
            try:
                log = KnowledgeSyncLog(
                    doc_id=doc_id,
                    action=action,
                    status=status,
                    error_message=error_message
                )
                db.add(log)
                db.commit()
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Failed to log sync: {e}")

    def sync_insert(self, doc_id: int, title: str, content: str, category: str):
        try:
            self.init_services()

            embedding = self.embedding_service.encode_single(content)

            self.milvus_service.insert_vectors(
                doc_ids=[doc_id],
                contents=[content[:2000]],
                embeddings=[embedding],
                categories=[category]
            )

            self.bm25_service.add_document(
                doc_id=doc_id,
                content=content,
                category=category
            )
            self.bm25_service.save_index()

            self._log_sync(doc_id, "insert", "success")
            logger.info(f"Auto-synced new document: id={doc_id}, title={title}")
        except Exception as e:
            self._log_sync(doc_id, "insert", "failed", str(e))
            logger.error(f"Failed to sync new document {doc_id}: {e}")

    def sync_update(self, doc_id: int, title: str, content: str, category: str):
        try:
            self.init_services()

            self.milvus_service.delete_by_doc_id(doc_id)
            self.bm25_service.remove_document(doc_id)

            embedding = self.embedding_service.encode_single(content)

            self.milvus_service.insert_vectors(
                doc_ids=[doc_id],
                contents=[content[:2000]],
                embeddings=[embedding],
                categories=[category]
            )

            self.bm25_service.add_document(
                doc_id=doc_id,
                content=content,
                category=category
            )
            self.bm25_service.save_index()

            self._log_sync(doc_id, "update", "success")
            logger.info(f"Auto-synced updated document: id={doc_id}, title={title}")
        except Exception as e:
            self._log_sync(doc_id, "update", "failed", str(e))
            logger.error(f"Failed to sync updated document {doc_id}: {e}")

    def sync_delete(self, doc_id: int):
        try:
            self.init_services()

            self.milvus_service.delete_by_doc_id(doc_id)
            self.bm25_service.remove_document(doc_id)
            self.bm25_service.save_index()

            self._log_sync(doc_id, "delete", "success")
            logger.info(f"Auto-synced deleted document: id={doc_id}")
        except Exception as e:
            self._log_sync(doc_id, "delete", "failed", str(e))
            logger.error(f"Failed to sync deleted document {doc_id}: {e}")

    def mark_for_update(self, doc_id: int, data: dict):
        with self._lock:
            self._pending_updates[doc_id] = data

    def get_pending_update(self, doc_id: int) -> Optional[dict]:
        with self._lock:
            return self._pending_updates.pop(doc_id, None)


knowledge_sync_service = KnowledgeSyncService()


def setup_knowledge_events():
    from app.models import KnowledgeDoc

    @event.listens_for(KnowledgeDoc, 'after_insert')
    def on_knowledge_insert(mapper, connection, target):
        def sync_async():
            knowledge_sync_service.sync_insert(
                doc_id=target.id,
                title=target.title,
                content=target.content,
                category=target.category
            )

        thread = threading.Thread(target=sync_async)
        thread.daemon = True
        thread.start()

    @event.listens_for(KnowledgeDoc, 'before_update')
    def on_knowledge_before_update(mapper, connection, target):
        knowledge_sync_service.mark_for_update(target.id, {
            'title': target.title,
            'content': target.content,
            'category': target.category
        })

    @event.listens_for(KnowledgeDoc, 'after_update')
    def on_knowledge_after_update(mapper, connection, target):
        pending = knowledge_sync_service.get_pending_update(target.id)
        if not pending:
            return

        def sync_async():
            knowledge_sync_service.sync_update(
                doc_id=target.id,
                title=target.title,
                content=target.content,
                category=target.category
            )

        thread = threading.Thread(target=sync_async)
        thread.daemon = True
        thread.start()

    @event.listens_for(KnowledgeDoc, 'after_delete')
    def on_knowledge_delete(mapper, connection, target):
        def sync_async():
            knowledge_sync_service.sync_delete(doc_id=target.id)

        thread = threading.Thread(target=sync_async)
        thread.daemon = True
        thread.start()

    logger.info("Knowledge auto-sync events registered")
