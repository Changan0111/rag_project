from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import get_db
from app.models import ChatHistory, KnowledgeDoc, User, KnowledgeSyncLog
from app.api.routers.auth import get_current_admin
from app.models import User as UserModel
from app.services.semantic_cache_service import semantic_cache_service
from app.services.redis_service import redis_service
from app.services.embedding_service import embedding_service
from app.services.bm25_service import bm25_service
from datetime import datetime, timedelta
from typing import List, Optional
import numpy as np
import jieba
import re

router = APIRouter(prefix="/stats", tags=["统计"])

STOP_WORDS = {
    '的', '了', '是', '在', '我', '有', '和', '就', '不', '人', '都', '一', '一个',
    '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好',
    '自己', '这', '那', '什么', '怎么', '吗', '呢', '啊', '吧', '呀', '哦', '嗯',
    '知道', '请问', '想', '能', '可以', '应该', '需要', '帮忙', '帮助', '一下',
    '这个', '那个', '这些', '那些', '哪个', '哪些', '如何', '为什么', '哪', '几',
    '多', '少', '多长时间', '多少钱', '多久', '什么时候', '哪里', '哪儿', '怎样',
    '吗？', '？', '。', '，', '！', '、', '：', '；', '"', '"', ''', ''',
    '（', '）', '【', '】', '《', '》', '…', '—', '·'
}

def extract_keywords(text: str) -> List[str]:
    text = re.sub(r'[？?！!。，,、：:；;""''（）【】《》\s]+', ' ', text)
    words = jieba.lcut(text)
    keywords = []
    for word in words:
        word = word.strip()
        if len(word) >= 2 and word not in STOP_WORDS:
            if not word.isdigit():
                keywords.append(word)
    return keywords


@router.get("/overview")
def get_overview(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_admin)
):
    total_users = db.query(func.count(User.id)).scalar() or 0
    total_knowledge = db.query(func.count(KnowledgeDoc.id)).scalar() or 0
    total_conversations = db.query(func.count(ChatHistory.id)).filter(
        ChatHistory.role == 'user'
    ).scalar() or 0

    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_conversations = db.query(func.count(ChatHistory.id)).filter(
        ChatHistory.role == 'user',
        ChatHistory.created_at >= today
    ).scalar() or 0

    # 用户统计（真实数据）
    seven_days_ago = datetime.now() - timedelta(days=7)

    # 活跃用户：7天内有登录的用户（基于 last_login_at）
    active_users = db.query(func.count(User.id)).filter(
        User.last_login_at >= seven_days_ago
    ).scalar() or 0
    
    # 本周新增用户
    week_new_users = db.query(func.count(User.id)).filter(
        User.created_at >= seven_days_ago
    ).scalar() or 0
    
    # 今日注册用户
    today_new_users = db.query(func.count(User.id)).filter(
        User.created_at >= today
    ).scalar() or 0

    knowledge_by_category = db.query(
        KnowledgeDoc.category,
        func.count(KnowledgeDoc.id).label('count')
    ).group_by(KnowledgeDoc.category).all()

    category_stats = {item.category: item.count for item in knowledge_by_category}

    daily_conversations = db.query(
        func.date(ChatHistory.created_at).label('date'),
        func.count(ChatHistory.id).label('count')
    ).filter(
        ChatHistory.role == 'user',
        ChatHistory.created_at >= seven_days_ago
    ).group_by(func.date(ChatHistory.created_at)).all()

    daily_stats = [
        {"date": str(item.date), "count": item.count}
        for item in daily_conversations
    ]

    return {
        "total_users": total_users,
        "total_knowledge": total_knowledge,
        "total_conversations": total_conversations,
        "today_conversations": today_conversations,
        "active_users": active_users,          # ✅ 真实活跃用户数
        "week_new_users": week_new_users,      # ✅ 本周新增
        "today_new_users": today_new_users,    # ✅ 今日注册
        "knowledge_by_category": category_stats,
        "daily_conversations": daily_stats
    }


@router.get("/recent-users")
def get_recent_users(
    limit: int = Query(10, ge=1, le=50, description="返回用户数量"),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_admin)
):
    recent_users = db.query(User).order_by(
        User.created_at.desc()
    ).limit(limit).all()

    return [
        {
            "id": user.id,
            "username": user.username,
            "phone": user.phone,
            "created_at": user.created_at,
            "last_login_at": user.last_login_at
        }
        for user in recent_users
    ]


@router.get("/hot-questions")
def get_hot_questions(
    days: int = Query(7, ge=1, le=30),
    limit: int = Query(10, ge=1, le=50),
    similarity_threshold: float = Query(0.85, ge=0.5, le=1.0, description="相似度阈值"),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_admin)
):
    from app.models import HumanServiceSession
    
    start_date = datetime.now() - timedelta(days=days)
    
    handoff_sessions = db.query(HumanServiceSession.session_id).filter(
        HumanServiceSession.created_at >= start_date
    ).subquery()
    
    questions = db.query(ChatHistory).filter(
        ChatHistory.role == 'user',
        ChatHistory.created_at >= start_date,
        ~ChatHistory.session_id.in_(handoff_sessions)
    ).all()
    
    if not questions:
        return []
    
    question_list = [q.content for q in questions]
    user_id_list = [q.user_id for q in questions]
    
    user_ids = list(set(uid for uid in user_id_list if uid))
    users = db.query(User).filter(User.id.in_(user_ids)).all()
    user_map = {u.id: u.username for u in users}
    
    embeddings = embedding_service.encode(question_list)
    
    def cosine_similarity(vec1, vec2):
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(dot_product / (norm1 * norm2))
    
    question_groups = []
    used_indices = set()
    
    for i, (question, embedding) in enumerate(zip(question_list, embeddings)):
        if i in used_indices:
            continue
        
        similar_questions = [question]
        similar_usernames = [user_map.get(user_id_list[i], "未知用户")]
        similar_indices = [i]
        
        for j in range(i + 1, len(question_list)):
            if j in used_indices:
                continue
            
            sim = cosine_similarity(embedding, embeddings[j])
            if sim >= similarity_threshold:
                similar_questions.append(question_list[j])
                similar_usernames.append(user_map.get(user_id_list[j], "未知用户"))
                similar_indices.append(j)
        
        used_indices.update(similar_indices)
        
        question_groups.append({
            "question": question,
            "count": len(similar_questions),
            "similar_questions": similar_questions[:3],
            "askers": similar_usernames[:3]
        })
    
    question_groups.sort(key=lambda x: x["count"], reverse=True)
    
    return question_groups[:limit]


@router.get("/chat-logs")
def get_chat_logs(
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    session_id: Optional[str] = Query(None, description="会话ID"),
    keyword: Optional[str] = Query(None, description="关键词搜索"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_admin)
):
    query = db.query(ChatHistory).filter(ChatHistory.role == 'user')
    
    if start_date:
        query = query.filter(ChatHistory.created_at >= datetime.strptime(start_date, "%Y-%m-%d"))
    if end_date:
        end_datetime = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
        query = query.filter(ChatHistory.created_at < end_datetime)
    if session_id:
        query = query.filter(ChatHistory.session_id == session_id)
    if keyword:
        query = query.filter(ChatHistory.content.contains(keyword))
    
    total = query.count()
    
    logs = query.order_by(ChatHistory.created_at.desc()).offset(offset).limit(limit).all()
    
    user_ids = list(set([log.user_id for log in logs if log.user_id]))
    users = db.query(User).filter(User.id.in_(user_ids)).all()
    user_map = {u.id: u.username for u in users}
    
    return {
        "total": total,
        "items": [
            {
                "id": log.id,
                "session_id": log.session_id,
                "user_id": log.user_id,
                "username": user_map.get(log.user_id, "未知用户"),
                "content": log.content,
                "created_at": log.created_at
            }
            for log in logs
        ]
    }


@router.get("/session-detail/{session_id}")
def get_session_detail(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_admin)
):
    histories = db.query(ChatHistory).filter(
        ChatHistory.session_id == session_id
    ).order_by(ChatHistory.created_at.asc()).all()
    
    return [
        {
            "id": h.id,
            "role": h.role,
            "content": h.content,
            "created_at": h.created_at
        }
        for h in histories
    ]


@router.get("/conversation-stats")
def get_conversation_stats(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_admin)
):
    import json
    
    total_sessions = db.query(func.count(func.distinct(ChatHistory.session_id))).scalar() or 0
    
    assistant_messages = db.query(ChatHistory).filter(
        ChatHistory.role == 'assistant',
        ChatHistory.reference_sources.isnot(None)
    ).all()
    
    category_counts = {}
    session_categories = {}
    
    for msg in assistant_messages:
        try:
            sources = msg.reference_sources if isinstance(msg.reference_sources, list) else json.loads(msg.reference_sources or '[]')
            if sources and len(sources) > 0:
                main_category = sources[0].get('category', 'other')
                category_counts[main_category] = category_counts.get(main_category, 0) + 1
                if msg.session_id not in session_categories:
                    session_categories[msg.session_id] = main_category
        except:
            pass
    
    total = sum(category_counts.values()) if category_counts else 0
    
    stats = []
    for cat, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
        percent = round((count / total * 100), 1) if total > 0 else 0
        stats.append({
            "category": cat,
            "count": count,
            "percent": percent
        })
    
    avg_response_time = 1.2
    avg_turns = 3.2
    
    if len(assistant_messages) > 0:
        sessions_data = {}
        for msg in db.query(ChatHistory).filter(
            ChatHistory.session_id.in_([m.session_id for m in assistant_messages])
        ).order_by(ChatHistory.created_at.asc()).all():
            if msg.session_id not in sessions_data:
                sessions_data[msg.session_id] = {"messages": [], "start": None, "end": None}
            sessions_data[msg.session_id]["messages"].append(msg)
            if sessions_data[msg.session_id]["start"] is None:
                sessions_data[msg.session_id]["start"] = msg.created_at
            sessions_data[msg.session_id]["end"] = msg.created_at
        
        turns_list = []
        response_times = []
        for sid, data in sessions_data.items():
            user_msgs = [m for m in data["messages"] if m.role == "user"]
            asst_msgs = [m for m in data["messages"] if m.role == "assistant"]
            turns_list.append(len(user_msgs))
            
            for i, asst in enumerate(asst_msgs):
                if i < len(user_msgs):
                    user_before = user_msgs[i]
                    if user_before.created_at and asst.created_at:
                        diff = (asst.created_at - user_before.created_at).total_seconds()
                        if diff > 0 and diff < 60:
                            response_times.append(diff)
        
        if turns_list:
            avg_turns = round(sum(turns_list) / len(turns_list), 1)
        if response_times:
            avg_response_time = round(sum(response_times) / len(response_times), 1)
    
    return {
        "total_sessions": total_sessions,
        "type_distribution": stats,
        "avg_response_time": avg_response_time,
        "avg_turns": avg_turns
    }


@router.get("/conversations-by-type/{category}")
def get_conversations_by_type(
    category: str,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_admin)
):
    import json
    
    assistant_messages = db.query(ChatHistory).filter(
        ChatHistory.role == 'assistant',
        ChatHistory.reference_sources.isnot(None)
    ).all()
    
    matching_session_ids = set()
    for msg in assistant_messages:
        try:
            sources = msg.reference_sources if isinstance(msg.reference_sources, list) else json.loads(msg.reference_sources or '[]')
            if sources:
                categories = [s.get('category') for s in sources]
                if category in categories:
                    matching_session_ids.add(msg.session_id)
        except:
            pass
    
    conversations = []
    for session_id in matching_session_ids:
        messages = db.query(ChatHistory).filter(
            ChatHistory.session_id == session_id
        ).order_by(ChatHistory.created_at.asc()).all()
        
        if not messages:
            continue
        
        first_user_msg = next((m for m in messages if m.role == 'user'), None)
        user_id = first_user_msg.user_id if first_user_msg else None
        
        user = db.query(User).filter(User.id == user_id).first() if user_id else None
        
        conversations.append({
            "session_id": session_id,
            "user_id": user_id,
            "username": user.username if user else "未知用户",
            "phone": user.phone if user else None,
            "first_message": first_user_msg.content[:100] if first_user_msg else "",
            "message_count": len([m for m in messages if m.role == 'user']),
            "created_at": messages[0].created_at,
            "last_active": messages[-1].created_at
        })
    
    conversations.sort(key=lambda x: x['last_active'], reverse=True)
    
    return conversations


@router.get("/today-conversations")
def get_today_conversations(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_admin)
):
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    today_user_messages = db.query(ChatHistory).filter(
        ChatHistory.role == 'user',
        ChatHistory.created_at >= today
    ).all()
    
    total_count = len(today_user_messages)
    
    current_hour = datetime.now().hour
    current_hour_start = today.replace(hour=current_hour)
    current_hour_end = current_hour_start + timedelta(hours=1)
    
    current_hour_count = db.query(func.count(ChatHistory.id)).filter(
        ChatHistory.role == 'user',
        ChatHistory.created_at >= current_hour_start,
        ChatHistory.created_at < current_hour_end
    ).scalar() or 0
    
    hourly_stats = []
    for hour in range(24):
        hour_start = today.replace(hour=hour)
        hour_end = hour_start + timedelta(hours=1)
        
        count = 0
        for msg in today_user_messages:
            if msg.created_at and hour_start <= msg.created_at < hour_end:
                count += 1
        
        hourly_stats.append({
            "hour": f"{hour:02d}:00",
            "count": count
        })
    
    peak_hour_entry = max(hourly_stats, key=lambda x: x['count']) if hourly_stats else None
    peak_hour_range = f"{peak_hour_entry['hour']}-{int(peak_hour_entry['hour'].split(':')[0]) + 1:02d}:00" if peak_hour_entry and peak_hour_entry['count'] > 0 else "-"
    
    total_so_far = sum(h['count'] for h in hourly_stats if h['hour'] <= f"{current_hour:02d}:00")
    
    if current_hour < 20 and total_so_far > 0:
        hours_passed = current_hour + 1
        avg_per_hour = total_so_far / hours_passed
        remaining_hours = 24 - current_hour - 1
        estimated_total = int(total_so_far + (avg_per_hour * remaining_hours))
    else:
        estimated_total = total_so_far
    
    return {
        "total_count": total_count,
        "current_hour_count": current_hour_count,
        "current_hour": f"{current_hour:02d}:00-{current_hour + 1:02d}:00" if current_hour < 23 else f"{current_hour:02d}:00-24:00",
        "peak_hour_range": peak_hour_range,
        "estimated_total": estimated_total,
        "hourly_distribution": hourly_stats
    }


@router.get("/today-recent-messages")
def get_today_recent_messages(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_admin)
):
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    messages = db.query(ChatHistory).filter(
        ChatHistory.role == 'user',
        ChatHistory.created_at >= today
    ).order_by(ChatHistory.created_at.desc()).limit(limit).all()
    
    result = []
    for msg in messages:
        username = "匿名用户"
        if msg.user_id:
            user = db.query(User).filter(User.id == msg.user_id).first()
            if user:
                username = user.username
        
        result.append({
            "id": msg.id,
            "username": username,
            "content": msg.content,
            "created_at": msg.created_at,
            "session_id": msg.session_id
        })
    
    return result


@router.get("/sync-status")
def get_sync_status(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_admin)
):
    recent_logs = db.query(KnowledgeSyncLog).order_by(
        KnowledgeSyncLog.created_at.desc()
    ).limit(10).all()
    
    success_count = db.query(func.count(KnowledgeSyncLog.id)).filter(
        KnowledgeSyncLog.status == 'success'
    ).scalar() or 0
    
    failed_count = db.query(func.count(KnowledgeSyncLog.id)).filter(
        KnowledgeSyncLog.status == 'failed'
    ).scalar() or 0
    
    return {
        "success_count": success_count,
        "failed_count": failed_count,
        "recent_logs": [
            {
                "id": log.id,
                "doc_id": log.doc_id,
                "action": log.action,
                "status": log.status,
                "error_message": log.error_message,
                "created_at": log.created_at
            }
            for log in recent_logs
        ]
    }


@router.delete("/sync-logs")
def clear_sync_logs(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_admin)
):
    deleted_count = db.query(KnowledgeSyncLog).delete()
    db.commit()
    
    return {"message": f"已清除 {deleted_count} 条同步记录", "deleted_count": deleted_count}


@router.get("/cache/stats")
def get_cache_stats(
    current_user: UserModel = Depends(get_current_admin)
):
    cache_stats = semantic_cache_service.get_stats()
    redis_stats = redis_service.get_stats()
    memory_stats = redis_service.get_memory_usage()
    db_size = redis_service.get_db_size()
    
    return {
        "semantic_cache": cache_stats,
        "redis": redis_stats,
        "memory": memory_stats,
        "db_size": db_size
    }


@router.get("/cache/list")
def get_cache_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    current_user: UserModel = Depends(get_current_admin)
):
    return semantic_cache_service.get_cache_list(page, page_size, keyword)


@router.get("/cache/debug")
def debug_cache(
    current_user: UserModel = Depends(get_current_admin)
):
    if not redis_service.is_enabled():
        return {"error": "Redis not enabled"}
    
    try:
        all_keys = redis_service._client.keys("*")
        cache_keys = redis_service._client.keys("rag:cache:*")
        embedding_keys = redis_service._client.keys("rag:embedding:*")
        
        sample_data = []
        for key in cache_keys[:3]:
            raw_value = redis_service._client.get(key)
            parsed_value = redis_service.get(key)
            sample_data.append({
                "key": key,
                "raw_value_type": type(raw_value).__name__,
                "raw_value_preview": str(raw_value)[:200] if raw_value else None,
                "parsed_value": parsed_value
            })
        
        return {
            "total_keys_in_redis": len(all_keys),
            "cache_keys_count": len(cache_keys),
            "embedding_keys_count": len(embedding_keys),
            "cache_keys": cache_keys[:10],
            "embedding_keys": embedding_keys[:10],
            "sample_data": sample_data
        }
    except Exception as e:
        return {"error": str(e)}


@router.get("/cache/detail/{key:path}")
def get_cache_detail(
    key: str,
    current_user: UserModel = Depends(get_current_admin)
):
    result = semantic_cache_service.get_cache_detail(key)
    if not result.get("enabled"):
        return {"error": "Redis未启用"}
    if not result.get("found"):
        return {"error": "缓存不存在"}
    return result


@router.delete("/cache/key/{key:path}")
def delete_cache_key(
    key: str,
    current_user: UserModel = Depends(get_current_admin)
):
    success = semantic_cache_service.delete_cache_by_key(key)
    if success:
        return {"message": "缓存已删除", "key": key}
    return {"error": "删除失败或缓存不存在"}


@router.delete("/cache/keys")
def delete_cache_keys(
    keys: List[str] = Query(..., description="要删除的缓存键列表"),
    current_user: UserModel = Depends(get_current_admin)
):
    deleted_count = semantic_cache_service.delete_cache_by_keys(keys)
    return {"message": f"已删除 {deleted_count} 条缓存", "deleted_count": deleted_count}


@router.delete("/cache/clear")
def clear_cache(
    current_user: UserModel = Depends(get_current_admin)
):
    semantic_cache_service.clear_all()
    
    return {"message": "缓存已清除"}


@router.get("/bm25/index")
def get_bm25_index_status(
    current_user: UserModel = Depends(get_current_admin)
):
    stats = bm25_service.get_stats()
    info = bm25_service.get_index_info()
    
    return {
        "stats": stats,
        "index_info": info
    }


@router.post("/bm25/save")
def save_bm25_index(
    current_user: UserModel = Depends(get_current_admin)
):
    success = bm25_service.save_index()
    if success:
        return {"message": "BM25 索引已保存", "stats": bm25_service.get_stats()}
    return {"error": "保存失败"}


@router.post("/bm25/rebuild")
def rebuild_bm25_index(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_admin)
):
    from app.models import KnowledgeDoc
    
    docs = db.query(KnowledgeDoc).all()
    bm25_service.clear()
    
    for doc in docs:
        bm25_service.add_document(
            doc_id=doc.id,
            content=doc.content,
            category=doc.category
        )
    
    bm25_service.save_index()
    
    return {
        "message": "BM25 索引已重建并保存",
        "doc_count": len(docs),
        "stats": bm25_service.get_stats()
    }
