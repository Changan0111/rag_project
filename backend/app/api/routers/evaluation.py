import logging
import math
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.routers.auth import get_current_admin
from app.services.evaluation_service import evaluation_service
from app.models import EvaluationRecord

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/evaluation", tags=["evaluation"])


def _safe_float(value, digits: Optional[int] = None):
    if value is None:
        return None

    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None

    if not math.isfinite(numeric):
        return None

    if digits is not None:
        return round(numeric, digits)

    return numeric


class SingleEvaluationRequest(BaseModel):
    query: str
    answer: str
    contexts: List[str]
    ground_truth: Optional[str] = None


class BatchEvaluationRequest(BaseModel):
    session_ids: Optional[List[str]] = None
    limit: int = 10
    framework: str = "builtin"
    strictness: int = 1
    max_workers: int = 8
    timeout: int = 300


class RecallComparisonRequest(BaseModel):
    sample_limit: int = 5
    top_ks: List[int] = [3, 5, 10]
    retrieval_modes: List[str] = ["vector", "bm25", "hybrid"]
    vector_weights: List[float] = [0.3, 0.5, 0.7]
    best_sort_by: str = "hit_rate"


@router.post("/single")
async def evaluate_single(
    request: SingleEvaluationRequest,
    current_admin = Depends(get_current_admin)
):
    try:
        scores = await evaluation_service.evaluate_single(
            query=request.query,
            answer=request.answer,
            contexts=request.contexts,
            ground_truth=request.ground_truth
        )
        return {
            "success": True,
            "scores": scores
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch")
async def evaluate_batch(
    request: BatchEvaluationRequest,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    try:
        target_framework = (request.framework or "builtin").strip().lower()
        evaluated_count = db.query(EvaluationRecord).filter(
            EvaluationRecord.evaluation_framework == target_framework
        ).count()
        logger.info(f"[{target_framework}] 已有 {evaluated_count} 条已评估记录，将从第 {evaluated_count + 1} 条开始评估")
        
        results = await evaluation_service.evaluate_batch(
            db=db,
            session_ids=request.session_ids,
            limit=request.limit,
            offset=evaluated_count
        )
        
        if not results:
            return {
                "success": True,
                "results": [],
                "summary": {
                    "total_evaluations": 0,
                    "evaluated_count": evaluated_count,
                    "message": "没有更多新问题需要评估"
                }
            }
        
        actual_framework = 'builtin'
        
        summary = evaluation_service.get_evaluation_summary(results)
        summary['evaluated_count'] = evaluated_count
        
        for result in results:
            scores = result.get('scores', {})
            
            record = EvaluationRecord(
                session_id=result.get('session_id'),
                query=result.get('query'),
                answer=result.get('answer'),
                contexts=result.get('contexts'),
                ground_truth=result.get('ground_truth'),
                faithfulness_score=scores.get('faithfulness'),
                answer_relevancy_score=scores.get('answer_relevancy'),
                context_precision_score=scores.get('context_precision'),
                overall_score=scores.get('overall_score'),
                evaluation_framework=actual_framework
            )
            db.add(record)
        
        db.commit()
        
        return {
            "success": True,
            "results": results,
            "summary": summary
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recall-comparison")
async def compare_recall_configs(
    request: RecallComparisonRequest,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    try:
        results = await evaluation_service.compare_strict_recall_configs(
            db=db,
            sample_limit=request.sample_limit,
            top_ks=request.top_ks,
            retrieval_modes=request.retrieval_modes,
            vector_weights=request.vector_weights,
            best_sort_by=request.best_sort_by
        )
        return {
            "success": True,
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_evaluation_history(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    from app.models import ChatHistory
    from sqlalchemy import desc, func
    
    sessions = db.query(
        ChatHistory.session_id,
        func.min(ChatHistory.created_at).label('first_message'),
        func.max(ChatHistory.created_at).label('last_message'),
        func.count(ChatHistory.id).label('message_count')
    ).group_by(
        ChatHistory.session_id
    ).order_by(
        desc(func.max(ChatHistory.created_at))
    ).offset(offset).limit(limit).all()
    
    return {
        "success": True,
        "sessions": [{
            "session_id": s.session_id,
            "first_message": s.first_message.isoformat() if s.first_message else None,
            "last_message": s.last_message.isoformat() if s.last_message else None,
            "message_count": s.message_count
        } for s in sessions]
    }


@router.get("/summary")
async def get_evaluation_summary(
    framework: Optional[str] = None,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    from app.models import ChatHistory, EvaluationRecord
    from sqlalchemy import func, desc
    
    total_sessions = db.query(func.count(func.distinct(ChatHistory.session_id))).scalar()
    total_messages = db.query(func.count(ChatHistory.id)).scalar()
    user_messages = db.query(func.count(ChatHistory.id)).filter(
        ChatHistory.role == 'user'
    ).scalar()
    
    eval_query = db.query(EvaluationRecord)
    if framework:
        eval_query = eval_query.filter(EvaluationRecord.evaluation_framework == framework)
    
    total_evaluations = eval_query.count()
    
    avg_faithfulness = eval_query.with_entities(func.avg(EvaluationRecord.faithfulness_score)).scalar() or 0
    avg_relevancy = eval_query.with_entities(func.avg(EvaluationRecord.answer_relevancy_score)).scalar() or 0
    avg_precision = eval_query.with_entities(func.avg(EvaluationRecord.context_precision_score)).scalar() or 0
    avg_overall = eval_query.with_entities(func.avg(EvaluationRecord.overall_score)).scalar() or 0
    
    return {
        "success": True,
        "stats": {
            "total_sessions": total_sessions,
            "total_messages": total_messages,
            "user_messages": user_messages,
            "assistant_messages": total_messages - user_messages
        },
        "evaluation_stats": {
            "total_evaluations": total_evaluations,
            "average_scores": {
                "faithfulness": _safe_float(avg_faithfulness, 4) or 0,
                "answer_relevancy": _safe_float(avg_relevancy, 4) or 0,
                "context_precision": _safe_float(avg_precision, 4) or 0,
                "overall_score": _safe_float(avg_overall, 4) or 0
            }
        }
    }


@router.get("/records")
async def get_evaluation_records(
    limit: int = 50,
    offset: int = 0,
    framework: Optional[str] = None,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    from sqlalchemy import desc
    
    query = db.query(EvaluationRecord)
    if framework:
        query = query.filter(EvaluationRecord.evaluation_framework == framework)
    
    records = query.order_by(
        desc(EvaluationRecord.created_at)
    ).offset(offset).limit(limit).all()
    
    return {
        "success": True,
        "records": [{
            "id": r.id,
            "session_id": r.session_id,
            "query": r.query,
            "answer": r.answer,
            "contexts": r.contexts,
            "ground_truth": r.ground_truth,
            "scores": {
                "faithfulness": _safe_float(r.faithfulness_score),
                "answer_relevancy": _safe_float(r.answer_relevancy_score),
                "context_precision": _safe_float(r.context_precision_score),
                "overall_score": _safe_float(r.overall_score)
            },
            "framework": r.evaluation_framework,
            "created_at": r.created_at.isoformat() if r.created_at else None
        } for r in records]
    }


class DatasetItemRequest(BaseModel):
    question: str
    ground_truth: str
    category: Optional[str] = None
    relevant_doc_ids: Optional[List[int]] = None


class DatasetRelevantDocsRequest(BaseModel):
    relevant_doc_ids: List[int] = []


class DatasetItemUpdateRequest(BaseModel):
    question: Optional[str] = None
    ground_truth: Optional[str] = None
    category: Optional[str] = None
    relevant_doc_ids: Optional[List[int]] = None


class BackfillEmbeddingsResponse(BaseModel):
    success: bool
    message: str
    updated_count: int
    skipped_count: int
    failed_count: int


@router.get("/dataset")
async def get_dataset_items(
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    from app.models import EvaluationDataset
    
    items = db.query(EvaluationDataset).all()
    
    return {
        "success": True,
        "items": [{
            "id": item.id,
            "question": item.question,
            "ground_truth": item.ground_truth,
            "category": item.category,
            "relevant_doc_ids": item.relevant_doc_ids or [],
            "has_embedding": item.question_embedding is not None,
            "created_at": item.created_at.isoformat() if item.created_at else None
        } for item in items]
    }


@router.post("/dataset")
async def add_dataset_item(
    request: DatasetItemRequest,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    from app.models import EvaluationDataset
    from app.services.embedding_service import embedding_service
    
    embedding = embedding_service.encode_single(request.question)
    
    item = EvaluationDataset(
        question=request.question,
        ground_truth=request.ground_truth,
        category=request.category,
        relevant_doc_ids=request.relevant_doc_ids or [],
        question_embedding=embedding.tolist() if hasattr(embedding, 'tolist') else embedding
    )
    
    db.add(item)
    db.commit()
    db.refresh(item)
    
    return {
        "success": True,
        "id": item.id,
        "message": "测试数据添加成功"
    }


@router.post("/dataset/batch")
async def add_dataset_items_batch(
    items: List[DatasetItemRequest],
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    from app.models import EvaluationDataset
    from app.services.embedding_service import embedding_service
    
    added_count = 0
    for item_data in items:
        embedding = embedding_service.encode_single(item_data.question)
        
        item = EvaluationDataset(
            question=item_data.question,
            ground_truth=item_data.ground_truth,
            category=item_data.category,
            relevant_doc_ids=item_data.relevant_doc_ids or [],
            question_embedding=embedding.tolist() if hasattr(embedding, 'tolist') else embedding
        )
        db.add(item)
        added_count += 1
    
    db.commit()
    
    return {
        "success": True,
        "count": added_count,
        "message": f"成功添加 {added_count} 条测试数据"
    }


@router.put("/dataset/{item_id}/relevant-docs")
async def update_dataset_relevant_docs(
    item_id: int,
    request: DatasetRelevantDocsRequest,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    from app.models import EvaluationDataset

    item = db.query(EvaluationDataset).filter(EvaluationDataset.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="测试数据不存在")

    cleaned_doc_ids = []
    seen = set()
    for value in request.relevant_doc_ids:
        try:
            doc_id = int(value)
        except (TypeError, ValueError):
            continue

        if doc_id <= 0 or doc_id in seen:
            continue

        seen.add(doc_id)
        cleaned_doc_ids.append(doc_id)

    item.relevant_doc_ids = cleaned_doc_ids
    db.commit()
    db.refresh(item)

    return {
        "success": True,
        "item": {
            "id": item.id,
            "relevant_doc_ids": item.relevant_doc_ids or []
        },
        "message": "相关文档标注已更新"
    }


@router.put("/dataset/{item_id}")
async def update_dataset_item(
    item_id: int,
    request: DatasetItemUpdateRequest,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    from app.models import EvaluationDataset
    from app.services.embedding_service import embedding_service

    item = db.query(EvaluationDataset).filter(EvaluationDataset.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="测试数据不存在")

    if request.question is not None:
        item.question = request.question
        embedding = embedding_service.encode_single(request.question)
        item.question_embedding = embedding.tolist() if hasattr(embedding, 'tolist') else embedding

    if request.ground_truth is not None:
        item.ground_truth = request.ground_truth

    if request.category is not None:
        item.category = request.category

    if request.relevant_doc_ids is not None:
        cleaned_doc_ids = []
        seen = set()
        for value in request.relevant_doc_ids:
            try:
                doc_id = int(value)
            except (TypeError, ValueError):
                continue

            if doc_id <= 0 or doc_id in seen:
                continue

            seen.add(doc_id)
            cleaned_doc_ids.append(doc_id)

        item.relevant_doc_ids = cleaned_doc_ids

    db.commit()
    db.refresh(item)

    return {
        "success": True,
        "item": {
            "id": item.id,
            "question": item.question,
            "ground_truth": item.ground_truth,
            "category": item.category,
            "relevant_doc_ids": item.relevant_doc_ids or []
        },
        "message": "测试数据更新成功"
    }


@router.post("/dataset/backfill-embeddings", response_model=BackfillEmbeddingsResponse)
async def backfill_dataset_embeddings(
    force: bool = False,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    from app.models import EvaluationDataset
    from app.services.embedding_service import embedding_service

    query = db.query(EvaluationDataset)
    if not force:
        query = query.filter(EvaluationDataset.question_embedding.is_(None))

    items = query.all()
    updated_count = 0
    skipped_count = 0
    failed_count = 0

    for item in items:
        if not item.question or not item.question.strip():
            skipped_count += 1
            continue

        try:
            embedding = embedding_service.encode_single(item.question)
            item.question_embedding = (
                embedding.tolist() if hasattr(embedding, 'tolist') else embedding
            )
            updated_count += 1
        except Exception as e:
            failed_count += 1
            logger.error(f"Failed to backfill embedding for dataset item {item.id}: {e}")

    db.commit()

    message = (
        f"已回填 {updated_count} 条 question_embedding"
        if not force
        else f"已重建 {updated_count} 条 question_embedding"
    )

    return {
        "success": True,
        "message": message,
        "updated_count": updated_count,
        "skipped_count": skipped_count,
        "failed_count": failed_count,
    }


@router.delete("/dataset/{item_id}")
async def delete_dataset_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    from app.models import EvaluationDataset
    
    item = db.query(EvaluationDataset).filter(EvaluationDataset.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="测试数据不存在")
    
    db.delete(item)
    db.commit()
    
    return {
        "success": True,
        "message": "测试数据删除成功"
    }


@router.delete("/dataset")
async def clear_dataset(
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    from app.models import EvaluationDataset
    
    count = db.query(EvaluationDataset).delete()
    db.commit()
    
    return {
        "success": True,
        "message": f"已删除 {count} 条测试数据"
    }
