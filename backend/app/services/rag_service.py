import re
import logging
from typing import List, Optional, Tuple, AsyncGenerator
from sqlalchemy.orm import Session
from datetime import datetime
from app.services.milvus_service import milvus_service
from app.services.embedding_service import embedding_service
from app.services.llm_service import LLMService
from app.services.sensitive_service import sensitive_filter
from app.services.hybrid_search_service import hybrid_search_service
from app.services.semantic_cache_service import semantic_cache_service
from app.services.intent_classifier import intent_classifier, IntentType
from app.services.human_service import human_service
from app.core.config import settings
from app.models import Order, Logistics, LogisticsTrack, OrderItem, Product, ChatHistory, KnowledgeDoc
import uuid
import json

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一个专业的电商智能客服助手。你的职责是：
回答用户关于商品的问题，包括商品规格、功能、价格等
解答用户的售后政策问题，如退货、换货、保修等
帮助用户查询订单状态和物流信息

请根据提供的上下文信息准确回答用户问题。
重要规则：
如果上下文信息与用户问题相关，请基于上下文准确回答
如果上下文信息与用户问题不相关，请使用你自己的知识回答用户的一般性问题
只有当问题涉及本平台的具体商品、订单、售后政策等，且上下文中确实没有相关信息时，才告知用户无法回答并建议联系人工客服

【回答格式要求 - 必须严格遵守】
必须使用自然流畅的紧凑段落形式回答，禁止使用任何列表格式
禁止使用数字编号（如1. 2. 3. 或 1、2、3、）
禁止使用Markdown格式符号，包括星号(*)、井号(#)、反引号(`)、破折号(-)
如需分步骤或分点说明，必须使用"首先，"、"其次，"、"然后，"、"最后，"等连接词紧密衔接
禁止使用加粗、斜体等格式
【排版要求 - 关键】段落之间只保留一个换行符，严禁在段落之间添加空行或多余换行
整个回答应该是一段或多段紧密相连的文字，不要有任何额外的空白间隔
如果涉及具体数据（如价格、时间等），请准确引用
保持友好和专业的语气
使用中文回答"""

SYSTEM_PROMPT_NO_KNOWLEDGE = """你是一个友好的电商智能客服助手。
你可以使用自己的知识回答用户的一般性问题。对于常识性问题、概念解释、行业知识等，请根据你的知识给出准确、有帮助的回答。
只有当用户询问本平台的具体商品信息、订单状态、售后政策等需要实时数据或平台特定信息时，才告知用户这些信息需要查询系统，建议用户提供更多细节或联系人工客服。

【回答格式要求 - 必须严格遵守】
必须使用自然流畅的紧凑段落形式回答，禁止使用任何列表格式
禁止使用数字编号（如1. 2. 3. 或 1、2、3、）
禁止使用Markdown格式符号，包括星号(*)、井号(#)、反引号(`)、破折号(-)
如需分步骤或分点说明，必须使用"首先，"、"其次，"、"然后，"、"最后，"等连接词紧密衔接
禁止使用加粗、斜体等格式
【排版要求 - 关键】段落之间只保留一个换行符，严禁在段落之间添加空行或多余换行
整个回答应该是一段或多段紧密相连的文字，不要有任何额外的空白间隔
充分利用你的知识帮助用户
如果不确定某些信息，请礼貌地说明
保持友好和专业的语气
使用中文回答"""

KNOWLEDGE_SCORE_THRESHOLD = 0.3
MAX_HISTORY_TURNS = 5


class RAGService:
    def __init__(self):
        self.order_pattern = re.compile(r'(ORD\d{10,})')

    def get_session_history(self, db: Session, session_id: str, user_id: int, limit: int = MAX_HISTORY_TURNS) -> List[dict]:
        histories = db.query(ChatHistory).filter(
            ChatHistory.session_id == session_id,
            ChatHistory.user_id == user_id
        ).order_by(ChatHistory.created_at.desc()).limit(limit * 2).all()
        
        histories = list(reversed(histories))
        
        return [{
            "role": h.role,
            "content": h.content
        } for h in histories]

    def format_history_context(self, history: List[dict]) -> str:
        if not history:
            return ""
        
        history_parts = []
        for h in history:
            if h["role"] == "user":
                history_parts.append(f"用户：{h['content']}")
            else:
                history_parts.append(f"助手：{h['content']}")
        
        return "\n".join(history_parts)

    def detect_intent(self, query: str) -> str:
        intent_result = intent_classifier.classify(query)
        return intent_result.intent.value
    
    def detect_intent_with_confidence(self, query: str):
        return intent_classifier.classify(query)

    def extract_order_no(self, query: str) -> Optional[str]:
        match = self.order_pattern.search(query)
        return match.group(1) if match else None

    def get_order_info(self, db: Session, order_no: str, user_id: int) -> Optional[dict]:
        order = db.query(Order).filter(
            Order.order_no == order_no,
            Order.user_id == user_id
        ).first()
        
        if not order:
            return None

        order_items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
        items_info = []
        for item in order_items:
            product = db.query(Product).filter(Product.id == item.product_id).first()
            items_info.append({
                "product_name": product.name if product else "未知商品",
                "quantity": item.quantity,
                "unit_price": float(item.unit_price)
            })

        logistics = db.query(Logistics).filter(Logistics.order_id == order.id).first()
        logistics_info = None
        if logistics:
            tracks = db.query(LogisticsTrack).filter(
                LogisticsTrack.logistics_id == logistics.id
            ).order_by(LogisticsTrack.track_time.desc()).all()
            
            logistics_info = {
                "tracking_no": logistics.tracking_no,
                "carrier": logistics.carrier,
                "status": logistics.status,
                "current_location": logistics.current_location,
                "tracks": [{
                    "location": t.location,
                    "status": t.status,
                    "time": t.track_time.strftime("%Y-%m-%d %H:%M") if t.track_time else None
                } for t in tracks]
            }

        return {
            "order_no": order.order_no,
            "status": order.status,
            "total_amount": float(order.total_amount),
            "payment_method": order.payment_method,
            "created_at": order.created_at.strftime("%Y-%m-%d %H:%M"),
            "items": items_info,
            "logistics": logistics_info
        }

    def format_order_context(self, order_info: dict) -> str:
        status_map = {
            'pending': '待支付',
            'paid': '已支付',
            'shipped': '已发货',
            'delivered': '已送达',
            'cancelled': '已取消'
        }
        
        context = f"订单号：{order_info['order_no']}\n"
        context += f"订单状态：{status_map.get(order_info['status'], order_info['status'])}\n"
        context += f"订单金额：¥{order_info['total_amount']}\n"
        context += f"下单时间：{order_info['created_at']}\n"
        context += "商品信息：\n"
        for item in order_info['items']:
            context += f"  - {item['product_name']} x{item['quantity']}，单价¥{item['unit_price']}\n"
        
        if order_info['logistics']:
            logi = order_info['logistics']
            context += f"\n物流信息：\n"
            context += f"快递公司：{logi['carrier']}\n"
            context += f"快递单号：{logi['tracking_no']}\n"
            context += f"物流状态：{logi['status']}\n"
            if logi['tracks']:
                context += "物流轨迹：\n"
                for track in logi['tracks'][:5]:
                    context += f"  [{track['time']}] {track['location']} - {track['status']}\n"
        
        return context

    async def retrieve_knowledge(self, query: str, top_k: int = 5, use_hybrid: bool = True) -> List[dict]:
        logger.info(f"[检索] 开始检索，查询: {query}, top_k={top_k}")
        
        if use_hybrid:
            results = await hybrid_search_service.search(
                query=query,
                top_k=top_k
            )
        else:
            query_embedding = embedding_service.encode_single(query)
            results = milvus_service.search(query_embedding, top_k=top_k)
        
        logger.info(f"[检索] 检索完成，返回{len(results)}条结果")
        
        return results

    def build_context(self, query: str, knowledge_results: List[dict], order_info: Optional[dict] = None) -> str:
        context_parts = []
        
        if order_info:
            context_parts.append("【订单信息】\n" + self.format_order_context(order_info))
        
        if knowledge_results:
            context_parts.append("【相关知识】")
            for i, result in enumerate(knowledge_results[:3], 1):
                context_parts.append(f"{i}. {result['content'][:500]}")
        
        return "\n\n".join(context_parts)

    def _check_sensitive_filter(self, query: str) -> Tuple[bool, str, str]:
        """检查敏感词，返回(是否被阻断, 过滤后的查询, 错误消息)"""
        filter_result = sensitive_filter.check_and_filter(query)
        if filter_result["blocked"]:
            return True, "", "抱歉，您的消息包含违规内容，无法处理。请文明交流。"
        
        filtered_query = filter_result["filtered"] if filter_result["has_sensitive"] else query
        return False, filtered_query, ""

    def _check_semantic_cache(self, filtered_query: str) -> Optional[str]:
        """检查语义缓存，返回缓存的答案或None"""
        cached_result = semantic_cache_service.get(filtered_query)
        if cached_result:
            return cached_result.get("answer", "")
        return None

    def _save_chat_history(
        self, 
        db: Session, 
        session_id: str, 
        user_id: Optional[int], 
        query: str, 
        answer: str,
        sources: Optional[list] = None
    ) -> None:
        """保存对话历史"""
        if not user_id:
            return
        
        try:
            chat_history = ChatHistory(
                session_id=session_id,
                user_id=user_id,
                role="user",
                content=query,
                source="user"
            )
            db.add(chat_history)
            
            assistant_history = ChatHistory(
                session_id=session_id,
                user_id=user_id,
                role="assistant",
                content=answer,
                reference_sources=sources or [],
                source="bot"
            )
            db.add(assistant_history)
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"保存对话记录失败: {e}")

    def _get_doc_titles(self, db: Session, doc_ids: List[int]) -> dict:
        if not doc_ids:
            return {}
        docs = db.query(KnowledgeDoc.id, KnowledgeDoc.title).filter(
            KnowledgeDoc.id.in_(doc_ids)
        ).all()
        return {doc.id: doc.title for doc in docs}

    async def _retrieve_order_and_knowledge(
        self,
        db: Session,
        filtered_query: str,
        intent: str,
        user_id: Optional[int]
    ) -> Tuple[Optional[dict], List[dict]]:
        """检索订单信息和知识库，返回(订单信息, 知识库结果)"""
        order_info = None
        knowledge_results = []

        if intent == 'order' and user_id:
            order_no = self.extract_order_no(filtered_query)
            if order_no:
                order_info = self.get_order_info(db, order_no, user_id)
            
            knowledge_results = await self.retrieve_knowledge(filtered_query, top_k=3)
        elif intent == 'promotion':
            promotion_query = f"促销 优惠 活动 {filtered_query}"
            knowledge_results = await self.retrieve_knowledge(promotion_query, top_k=3)
        elif intent == 'member':
            member_query = f"会员 积分 等级 权益 {filtered_query}"
            knowledge_results = await self.retrieve_knowledge(member_query, top_k=4)
        else:
            knowledge_results = await self.retrieve_knowledge(filtered_query, top_k=4)
        
        return order_info, knowledge_results

    def _has_relevant_knowledge(self, knowledge_results: List[dict]) -> bool:
        return len(knowledge_results) > 0 and any(
            result.get('score', 0) >= KNOWLEDGE_SCORE_THRESHOLD for result in knowledge_results
        )

    def _should_transfer_to_human(
        self,
        intent: str,
        confidence: float,
        order_info: Optional[dict],
        knowledge_results: List[dict]
    ) -> bool:
        # 有订单信息时，不转人工（可以直接回答订单相关问题）
        if order_info:
            return False

        # 有相关知识时，不转人工（可以用知识库回答）
        if self._has_relevant_knowledge(knowledge_results):
            return False

        # 无相关知识且无订单信息时，需要转人工
        # 注意：置信度仅用于判断意图是否明确，但不作为是否转人工的决定因素
        # 只要知识库没有相关知识，就应该转人工，无论置信度高低
        if intent in {item.value for item in IntentType}:
            return True
        
        # 意图不明确时，也转人工
        return True

    def _transfer_to_human(
        self,
        db: Session,
        session_id: str,
        user_id: Optional[int],
        query: str,
        intent: str
    ) -> str:
        if not user_id:
            return "当前问题需要人工客服进一步处理，请登录后重试。"

        return human_service.enqueue_handoff(
            db=db,
            session_id=session_id,
            user_id=user_id,
            user_message=query,
            transfer_reason=f"{intent}_knowledge_missing"
        )

    def _build_prompt(
        self,
        filtered_query: str,
        context: str,
        history_context: str,
        context_type: str = "上下文"
    ) -> str:
        """构建提示词"""
        if history_context:
            prompt = f"""以下是之前的对话历史：
{history_context}

---

请根据以下{context_type}回答用户问题：
{context}

用户问题：{filtered_query}

请给出准确、专业的回答（注意结合对话历史理解用户意图）。"""
        else:
            prompt = f"""请根据以下{context_type}回答用户问题：
{context}

用户问题：{filtered_query}

请给出准确、专业的回答。"""
        
        return prompt

    async def generate_answer(
        self,
        query: str,
        db: Session,
        llm_service: LLMService,
        user_id: Optional[int] = None,
        session_id: Optional[str] = None
    ) -> Tuple[str, str, List[dict]]:
        if not session_id:
            session_id = str(uuid.uuid4())

        blocked, filtered_query, error_msg = self._check_sensitive_filter(query)
        if blocked:
            return error_msg, session_id, []

        cached_answer = self._check_semantic_cache(filtered_query)
        if cached_answer:
            self._save_chat_history(db, session_id, user_id, query, cached_answer)
            return cached_answer, session_id, []

        intent_result = self.detect_intent_with_confidence(filtered_query)
        intent = intent_result.intent.value
        confidence = intent_result.confidence
        
        logger.info(f"[意图识别] 意图: {intent}, 置信度: {confidence:.2f}, 匹配: {intent_result.matched_keywords}")

        history = []
        if user_id and session_id:
            history = self.get_session_history(db, session_id, user_id)
            logger.info(f"[多轮对话] 获取到{len(history)}条历史记录")

        if intent_classifier.is_low_confidence(confidence):
            logger.info(f"[意图处理] 低置信度({confidence:.2f})，直接转人工客服")
            answer = self._transfer_to_human(db, session_id, user_id, query, intent)
            return answer, session_id, []

        order_info, knowledge_results = await self._retrieve_order_and_knowledge(
            db, filtered_query, intent, user_id
        )

        logger.info(f"Knowledge results: {len(knowledge_results)} items")
        for r in knowledge_results[:3]:
            logger.debug(f"  - doc_id={r.get('doc_id')}, score={r.get('score'):.4f}")

        has_relevant_knowledge = self._has_relevant_knowledge(knowledge_results)

        logger.info(f"Has relevant knowledge: {has_relevant_knowledge} (threshold={KNOWLEDGE_SCORE_THRESHOLD})")

        history_context = self.format_history_context(history)

        if self._should_transfer_to_human(intent, confidence, order_info, knowledge_results):
            answer = self._transfer_to_human(db, session_id, user_id, query, intent)
            return answer, session_id, []

        if has_relevant_knowledge:
            filtered_results = [r for r in knowledge_results if r.get('score', 0) >= KNOWLEDGE_SCORE_THRESHOLD]
            context = self.build_context(filtered_query, filtered_results, order_info)
            prompt = self._build_prompt(filtered_query, context, history_context, "上下文信息")
            answer = await llm_service.generate(
                prompt=prompt,
                system_prompt=SYSTEM_PROMPT,
                temperature=0.3
            )
        else:
            if order_info:
                context = self.build_context(filtered_query, [], order_info)
                prompt = self._build_prompt(filtered_query, context, history_context, "订单信息")
                answer = await llm_service.generate(
                    prompt=prompt,
                    system_prompt=SYSTEM_PROMPT,
                    temperature=0.3
                )
            else:
                logger.info(f"[知识库检索] 无相关知识，使用通用知识回答")
                history_context = self.format_history_context(history)
                prompt = self._build_prompt(filtered_query, "", history_context, "")
                answer = await llm_service.generate(
                    prompt=prompt,
                    system_prompt=SYSTEM_PROMPT_NO_KNOWLEDGE,
                    temperature=0.3
                )

        sources = []
        if has_relevant_knowledge:
            filtered_results = [r for r in knowledge_results if r.get('score', 0) >= KNOWLEDGE_SCORE_THRESHOLD]
            doc_ids = [r.get("doc_id") for r in filtered_results if r.get("doc_id")]
            doc_titles = self._get_doc_titles(db, doc_ids)
            sources = [
                {
                    "doc_id": r.get("doc_id"),
                    "title": doc_titles.get(r.get("doc_id"), "") or r.get("title", ""),
                    "category": r.get("category", ""),
                    "score": round(r.get("score", 0), 4),
                    "content": (r.get("content", "") or "")[:120]
                }
                for r in filtered_results
            ]

        semantic_cache_service.set(filtered_query, {
            "query": filtered_query,
            "answer": answer,
            "sources": sources,
            "created_at": datetime.now().isoformat()
        })

        self._save_chat_history(db, session_id, user_id, query, answer, sources)

        return answer, session_id, sources

    async def generate_answer_stream(
        self,
        query: str,
        db: Session,
        llm_service: LLMService,
        user_id: Optional[int] = None,
        session_id: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        if not session_id:
            session_id = str(uuid.uuid4())

        filter_result = sensitive_filter.check_and_filter(query)
        if filter_result["blocked"]:
            yield f"data: {json.dumps({'type': 'error', 'content': '抱歉，您的消息包含违规内容，无法处理。请文明交流。', 'session_id': session_id}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'session_id': session_id}, ensure_ascii=False)}\n\n"
            return

        filtered_query = filter_result["filtered"] if filter_result["has_sensitive"] else query

        cached_result = semantic_cache_service.get(filtered_query)
        if cached_result:
            cached_sources = cached_result.get('sources', [])
            yield f"data: {json.dumps({'type': 'session', 'session_id': session_id}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'cached', 'content': cached_result.get('answer', ''), 'sources': cached_sources}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'session_id': session_id, 'sources': cached_sources}, ensure_ascii=False)}\n\n"
            
            if user_id:
                try:
                    chat_history = ChatHistory(
                        session_id=session_id,
                        user_id=user_id,
                        role="user",
                        content=query,
                        source="user"
                    )
                    db.add(chat_history)
                    
                    assistant_history = ChatHistory(
                        session_id=session_id,
                        user_id=user_id,
                        role="assistant",
                        content=cached_result.get('answer', ''),
                        reference_sources=cached_sources,
                        source="bot"
                    )
                    db.add(assistant_history)
                    db.commit()
                except Exception as e:
                    db.rollback()
                    print(f"保存缓存对话记录失败: {e}")
            return

        intent_result = self.detect_intent_with_confidence(filtered_query)
        intent = intent_result.intent.value
        confidence = intent_result.confidence
        
        logger.info(f"[意图识别-流式] 意图: {intent}, 置信度: {confidence:.2f}")

        order_info = None
        knowledge_results = []
        filtered_results = []  # 用于存储过滤后的结果，以便提取来源

        history = []
        if user_id and session_id:
            history = self.get_session_history(db, session_id, user_id)
            logger.info(f"[多轮对话-流式] 获取到{len(history)}条历史记录")

        history_context = self.format_history_context(history)
        
        if intent_classifier.is_low_confidence(confidence):
            logger.info(f"[意图处理-流式] 低置信度({confidence:.2f})，直接转人工客服")
            
            notice = self._transfer_to_human(db, session_id, user_id, query, intent)
            yield f"data: {json.dumps({'type': 'session', 'session_id': session_id}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'handoff', 'content': notice, 'session_id': session_id}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'session_id': session_id}, ensure_ascii=False)}\n\n"
            return
        else:
            if intent == 'order' and user_id:
                order_no = self.extract_order_no(filtered_query)
                if order_no:
                    order_info = self.get_order_info(db, order_no, user_id)
                knowledge_results = await self.retrieve_knowledge(filtered_query, top_k=4)
            elif intent == 'promotion':
                promotion_query = f"促销 优惠 活动 {filtered_query}"
                knowledge_results = await self.retrieve_knowledge(promotion_query, top_k=3)
            elif intent == 'member':
                member_query = f"会员 积分 等级 权益 {filtered_query}"
                knowledge_results = await self.retrieve_knowledge(member_query, top_k=4)
            else:
                knowledge_results = await self.retrieve_knowledge(filtered_query, top_k=4)

            has_relevant_knowledge = self._has_relevant_knowledge(knowledge_results)

            if self._should_transfer_to_human(intent, confidence, order_info, knowledge_results):
                notice = self._transfer_to_human(db, session_id, user_id, query, intent)
                yield f"data: {json.dumps({'type': 'session', 'session_id': session_id}, ensure_ascii=False)}\n\n"
                yield f"data: {json.dumps({'type': 'handoff', 'content': notice, 'session_id': session_id}, ensure_ascii=False)}\n\n"
                yield f"data: {json.dumps({'type': 'done', 'session_id': session_id}, ensure_ascii=False)}\n\n"
                return

            if has_relevant_knowledge:
                filtered_results = [r for r in knowledge_results if r.get('score', 0) >= KNOWLEDGE_SCORE_THRESHOLD]

                context = self.build_context(filtered_query, filtered_results, order_info)

                if history_context:
                    prompt = f"""以下是之前的对话历史：
{history_context}

---

请根据以下上下文信息回答用户问题：
上下文信息：
{context}

用户问题：{filtered_query}

请给出准确、专业的回答（注意结合对话历史理解用户意图）。"""
                else:
                    prompt = f"""请根据以下上下文信息回答用户问题：
上下文信息：
{context}

用户问题：{filtered_query}

请给出准确、专业的回答。"""

                system_prompt = SYSTEM_PROMPT
                temperature = 0.3
            else:
                if order_info:
                    context = self.build_context(filtered_query, [], order_info)
                    if history_context:
                        prompt = f"""以下是之前的对话历史：
{history_context}

---

请根据以下订单信息回答用户问题：
{context}

用户问题：{filtered_query}

请给出准确、专业的回答（注意结合对话历史理解用户意图）。"""
                    else:
                        prompt = f"""请根据以下订单信息回答用户问题：
{context}

用户问题：{filtered_query}

请给出准确、专业的回答。"""
                    
                    system_prompt = SYSTEM_PROMPT
                    temperature = 0.3
                else:
                    logger.info(f"[知识库检索-流式] 无相关知识，使用通用知识回答")
                    
                    yield f"data: {json.dumps({'type': 'session', 'session_id': session_id}, ensure_ascii=False)}\n\n"
                    
                    if history_context:
                        prompt = f"""以下是之前的对话历史：
{history_context}

---

用户问题：{filtered_query}

请给出准确、专业的回答（注意结合对话历史理解用户意图）。"""
                    else:
                        prompt = f"""用户问题：{filtered_query}

请给出准确、专业的回答。"""
                    
                    system_prompt = SYSTEM_PROMPT_NO_KNOWLEDGE
                    temperature = 0.3
                    
                    full_answer = ""
                    async for chunk in llm_service.generate_stream(
                        prompt=prompt,
                        system_prompt=system_prompt,
                        temperature=temperature
                    ):
                        full_answer += chunk
                        yield f"data: {json.dumps({'type': 'content', 'content': chunk}, ensure_ascii=False)}\n\n"
                    
                    semantic_cache_service.set(filtered_query, {
                        "query": filtered_query,
                        "answer": full_answer,
                        "sources": [],
                        "created_at": datetime.now().isoformat()
                    })
                    
                    if user_id:
                        try:
                            chat_history = ChatHistory(
                                session_id=session_id,
                                user_id=user_id,
                                role="user",
                                content=query,
                                source="user"
                            )
                            db.add(chat_history)
                            
                            assistant_history = ChatHistory(
                                session_id=session_id,
                                user_id=user_id,
                                role="assistant",
                                content=full_answer,
                                reference_sources=[],
                                source="bot"
                            )
                            db.add(assistant_history)
                            db.commit()
                        except Exception as e:
                            db.rollback()
                            print(f"保存对话记录失败: {e}")
                    
                    yield f"data: {json.dumps({'type': 'done', 'session_id': session_id}, ensure_ascii=False)}\n\n"
                    return

        yield f"data: {json.dumps({'type': 'session', 'session_id': session_id}, ensure_ascii=False)}\n\n"

        full_answer = ""
        async for chunk in llm_service.generate_stream(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature
        ):
            full_answer += chunk
            yield f"data: {json.dumps({'type': 'content', 'content': chunk}, ensure_ascii=False)}\n\n"

        sources = []
        if has_relevant_knowledge and filtered_results:
            doc_ids = [r.get("doc_id") for r in filtered_results if r.get("doc_id")]
            doc_titles = self._get_doc_titles(db, doc_ids)
            sources = [
                {
                    "doc_id": r.get("doc_id"),
                    "title": doc_titles.get(r.get("doc_id"), "") or r.get("title", ""),
                    "category": r.get("category", ""),
                    "score": round(r.get("score", 0), 4),
                    "content": (r.get("content", "") or "")[:120]
                }
                for r in filtered_results
            ]

        semantic_cache_service.set(filtered_query, {
            "query": filtered_query,
            "answer": full_answer,
            "sources": sources,
            "created_at": datetime.now().isoformat()
        })

        if user_id:
            try:
                chat_history = ChatHistory(
                    session_id=session_id,
                    user_id=user_id,
                    role="user",
                    content=query,
                    source="user"
                )
                db.add(chat_history)
                
                assistant_history = ChatHistory(
                    session_id=session_id,
                    user_id=user_id,
                    role="assistant",
                    content=full_answer,
                    reference_sources=sources,
                    source="bot"
                )
                db.add(assistant_history)
                db.commit()
            except Exception as e:
                db.rollback()
                print(f"保存对话记录失败: {e}")
        
        # ✅ 调试日志：打印 sources 数据
        logger.info(f"[参考来源] 准备返回 {len(sources)} 条来源: {sources}")
        
        yield f"data: {json.dumps({'type': 'done', 'session_id': session_id, 'sources': sources}, ensure_ascii=False)}\n\n"

    def get_chat_history(self, db: Session, session_id: str, user_id: int, limit: int = 50) -> List[dict]:
        histories = db.query(ChatHistory).filter(
            ChatHistory.session_id == session_id,
            ChatHistory.user_id == user_id
        ).order_by(ChatHistory.created_at.asc()).limit(limit).all()
        
        return [{
            "id": h.id,
            "session_id": h.session_id,
            "role": h.role,
            "content": h.content,
            "source": h.source,
            "sources": h.reference_sources or [],
            "created_at": h.created_at
        } for h in histories]

    def get_user_sessions(self, db: Session, user_id: int, limit: int = 20) -> List[dict]:
        from sqlalchemy import func
        
        sessions = db.query(
            ChatHistory.session_id,
            func.min(ChatHistory.created_at).label('created_at'),
            func.max(ChatHistory.created_at).label('updated_at'),
            func.count(ChatHistory.id).label('message_count')
        ).filter(
            ChatHistory.user_id == user_id
        ).group_by(
            ChatHistory.session_id
        ).order_by(
            func.max(ChatHistory.created_at).desc()
        ).limit(limit).all()
        
        result = []
        for session in sessions:
            first_msg = db.query(ChatHistory).filter(
                ChatHistory.session_id == session.session_id,
                ChatHistory.user_id == user_id,
                ChatHistory.role == 'user'
            ).order_by(ChatHistory.created_at.asc()).first()
            
            last_msg = db.query(ChatHistory).filter(
                ChatHistory.session_id == session.session_id,
                ChatHistory.user_id == user_id,
                ChatHistory.role == 'assistant'
            ).order_by(ChatHistory.created_at.desc()).first()
            
            result.append({
                "session_id": session.session_id,
                "first_message": first_msg.content[:50] + "..." if first_msg and len(first_msg.content) > 50 else (first_msg.content if first_msg else ""),
                "last_message": last_msg.content[:50] + "..." if last_msg and len(last_msg.content) > 50 else (last_msg.content if last_msg else ""),
                "message_count": session.message_count,
                "created_at": session.created_at,
                "updated_at": session.updated_at
            })
        
        return result

    def clear_session(self, db: Session, session_id: str, user_id: int):
        db.query(ChatHistory).filter(
            ChatHistory.session_id == session_id,
            ChatHistory.user_id == user_id
        ).delete()
        human_service.remove_session(db, session_id, user_id)
        db.commit()


rag_service = RAGService()
