from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models import KnowledgeDoc, KnowledgeSyncLog, User
from app.schemas import KnowledgeDocCreate, KnowledgeDocResponse
from app.services.milvus_service import milvus_service
from app.services.embedding_service import embedding_service
from app.services.bm25_service import bm25_service
from app.services.hybrid_search_service import hybrid_search_service
from app.utils.text_chunker import batch_split_documents
from app.api.routers.auth import get_current_admin
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/knowledge", tags=["知识库"])


@router.post("", response_model=KnowledgeDocResponse)
def add_knowledge(
    doc_data: KnowledgeDocCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    new_doc = KnowledgeDoc(
        title=doc_data.title,
        content=doc_data.content,
        category=doc_data.category,
        source=doc_data.source
    )
    
    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)
    
    return new_doc


@router.put("/{doc_id}", response_model=KnowledgeDocResponse)
def update_knowledge(
    doc_id: int,
    doc_data: KnowledgeDocCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    doc = db.query(KnowledgeDoc).filter(KnowledgeDoc.id == doc_id).first()
    
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    doc.title = doc_data.title
    doc.content = doc_data.content
    doc.category = doc_data.category
    doc.source = doc_data.source
    
    db.commit()
    db.refresh(doc)
    
    return doc


@router.get("")
def get_knowledge_list(
    category: Optional[str] = Query(None, description="分类筛选"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    query = db.query(KnowledgeDoc)
    
    if category:
        query = query.filter(KnowledgeDoc.category == category)
    
    total = query.count()
    docs = query.order_by(KnowledgeDoc.created_at.asc()).offset(offset).limit(limit).all()
    
    return {
        "items": docs,
        "total": total
    }


@router.get("/{doc_id}", response_model=KnowledgeDocResponse)
def get_knowledge_detail(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    doc = db.query(KnowledgeDoc).filter(KnowledgeDoc.id == doc_id).first()
    
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    return doc


@router.delete("/{doc_id}")
def delete_knowledge(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    doc = db.query(KnowledgeDoc).filter(KnowledgeDoc.id == doc_id).first()
    
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    db.delete(doc)
    db.commit()
    
    return {"message": "文档已删除"}


@router.post("/sync")
def sync_knowledge_to_milvus(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    docs = db.query(KnowledgeDoc).all()
    
    if not docs:
        return {"message": "没有需要同步的文档"}
    
    collection_recreated = milvus_service.ensure_hnsw_index()
    
    doc_input = [{"doc_id": doc.id, "content": doc.content, "category": doc.category, "title": doc.title} for doc in docs]
    chunks = batch_split_documents(doc_input)
    
    chunk_texts = [c["content"] for c in chunks]
    all_embeddings = embedding_service.encode(chunk_texts)

    bm25_service.clear()
    
    doc_ids = []
    contents = []
    embeddings = []
    categories = []
    chunk_ids = []
    
    for i, chunk in enumerate(chunks):
        if not collection_recreated:
            milvus_service.delete_by_doc_id(chunk["doc_id"])
        doc_ids.append(chunk["doc_id"])
        contents.append(chunk["content"])
        embeddings.append(all_embeddings[i])
        categories.append(chunk["category"])
        chunk_ids.append(chunk["chunk_index"])

        bm25_service.add_document(
            doc_id=chunk["doc_id"],
            content=chunk["content"],
            category=chunk["category"],
            chunk_index=chunk["chunk_index"]
        )
    
    milvus_service.insert_vectors(
        doc_ids=doc_ids,
        contents=contents,
        embeddings=embeddings,
        categories=categories,
        chunk_ids=chunk_ids
    )
    
    bm25_service.save_index()
    
    for doc in docs:
        sync_log = KnowledgeSyncLog(
            doc_id=doc.id,
            action='update',
            status='success'
        )
        db.add(sync_log)
    
    db.commit()
    
    milvus_stats = milvus_service.get_collection_stats()
    bm25_stats = bm25_service.get_stats()
    
    result = {
        "message": f"已同步 {len(docs)} 条知识文档（切分为 {len(chunks)} 个文本块）到向量数据库和BM25索引",
        "milvus": {
            "index_type": milvus_stats.get("index_type", "unknown"),
            "index_upgraded": milvus_stats.get("index_type") == "HNSW",
            "collection_recreated": collection_recreated,
            "num_entities": milvus_stats.get("num_entities", 0)
        },
        "bm25": {
            "doc_count": bm25_stats.get("doc_count", 0),
            "avg_doc_len": bm25_stats.get("avg_doc_len", 0),
            "vocab_size": bm25_stats.get("vocab_size", 0)
        }
    }
    
    logger.info(f"Sync completed: {result}")
    return result


@router.get("/stats/index")
def get_index_stats(
    current_user: User = Depends(get_current_admin)
):
    stats = hybrid_search_service.get_stats()
    return stats


@router.get("/sync/logs")
def get_sync_logs(
    doc_id: Optional[int] = Query(None, description="文档ID"),
    status: Optional[str] = Query(None, description="状态筛选"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    query = db.query(KnowledgeSyncLog)
    
    if doc_id:
        query = query.filter(KnowledgeSyncLog.doc_id == doc_id)
    if status:
        query = query.filter(KnowledgeSyncLog.status == status)
    
    logs = query.order_by(KnowledgeSyncLog.created_at.desc()).limit(limit).all()
    
    return [{
        "id": log.id,
        "doc_id": log.doc_id,
        "action": log.action,
        "status": log.status,
        "error_message": log.error_message,
        "created_at": log.created_at
    } for log in logs]
