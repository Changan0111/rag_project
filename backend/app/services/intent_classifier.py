import re
import logging
import numpy as np
from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class IntentType(Enum):
    PRODUCT = "product"
    ORDER = "order"
    POLICY = "policy"
    PROMOTION = "promotion"
    MEMBER = "member"
    PAYMENT = "payment"
    TECHNICAL = "technical"


@dataclass
class IntentResult:
    intent: IntentType
    confidence: float
    matched_keywords: list
    reasoning: str


INTENT_KEYWORDS = {
    IntentType.ORDER: [
        "订单", "物流", "快递", "发货", "送达", "签收", "配送", "运单", "包裹", "到哪了",
        "运费", "包邮", "配送时效", "几天到", "物流追踪", "快递公司",
        "上门安装", "预约配送", "同城急送", "大件商品", "偏远地区",
        "签收验货", "代签", "包裹破损", "物流延迟", "催件"
    ],
    IntentType.POLICY: [
        "退货", "换货", "保修", "售后", "退款", "维修", "退换", "质量", "能退吗", "能换吗",
        "7天无理由", "15天", "质量问题", "外观损坏", "包装完好",
        "退货流程", "换货流程", "审核", "寄回地址",
        "保修期", "保修范围", "人为损坏", "进液", "摔落", "私自拆修",
        "维修流程", "售后申请", "凭证", "购买凭证"
    ],
    IntentType.PROMOTION: [
        "优惠", "优惠券", "满减", "活动", "折扣", "促销", "特价", "秒杀", "便宜",
        "618", "双11", "双12", "年货节", "女王节", "购物节",
        "以旧换新", "折上折", "限时", "团购", "拼团",
        "新人优惠", "首单", "满减规则", "优惠券使用", "积分兑换"
    ],
    IntentType.PRODUCT: [
        "商品", "产品", "规格", "参数", "功能", "价格", "多少钱", "尺寸", "颜色", "型号", "有货吗", "推荐",
        "手机", "iPhone", "华为", "小米", "三星", "OPPO", "vivo", "荣耀",
        "屏幕", "电池", "充电", "摄像头", "拍照", "处理器", "内存", "存储",
        "电脑", "笔记本", "MacBook", "ThinkPad", "戴尔", "联想",
        "冰箱", "洗衣机", "空调", "吸尘器", "洗碗机", "电饭煲", "净化器",
        "容量", "升", "公斤", "匹", "变频", "能效", "噪音",
        "衣服", "T恤", "鞋子", "运动鞋", "瑜伽裤", "牛仔外套", "尺码",
        "护肤品", "精华", "面膜", "爽肤水", "面霜", "SK-II", "雅诗兰黛", "兰蔻",
        "成分", "肤质", "保湿", "抗老", "美白",
        "哪个好", "怎么选", "对比", "区别", "推荐吗", "适合", "性价比"
    ],
    IntentType.MEMBER: [
        "会员", "积分", "等级", "权益", "银卡", "金卡", "钻石", "会员日", "专属客服", "极速退款",
        "升级条件", "保级", "降级", "消费金额", "生日礼遇", "双倍积分",
        "五倍积分", "专属折扣", "免运费券", "优先购买权", "VIP特权",
        "钻石会员95折", "企业客户", "商务合作"
    ],
    IntentType.PAYMENT: [
        "支付", "付款", "分期", "花呗", "白条", "信用卡", "支付宝", "微信",
        "发票", "开票", "专票", "普票", "电子票", "纸票", "税号", "抬头",
        "对公转账", "企业付款", "账期", "月结", "报销", "补票",
        "价保", "降价", "补差价", "价格保护"
    ],
    IntentType.TECHNICAL: [
        "怎么用", "如何操作", "设置方法", "使用教程", "省电技巧",
        "保养方法", "清洁维护", "故障排查", "系统更新", "APP功能",
        "连接蓝牙", "WiFi设置", "账号注册", "密码重置", "数据迁移",
        "配件选购", "安装教程", "注意事项", "兼容性",
        "使用技巧", "功能介绍", "操作指南", "配置方法"
    ]
}

ORDER_PATTERN = re.compile(r'(ORD\d{10,})')

INTENT_EXAMPLES: Dict[IntentType, List[str]] = {
    IntentType.PRODUCT: [
        "这个商品多少钱",
        "有什么功能",
        "推荐一款手机",
        "这个产品怎么样",
        "有什么颜色可选",
        "尺寸是多少",
        "这个型号有什么区别",
        "产品参数是什么",
        "有现货吗",
        "这款和那款有什么区别",
        "iPhone 15 Pro Max的电池容量是多少",
        "华为Mate 60 Pro支持5G网络吗",
        "MacBook Pro 16英寸的续航时间是多久",
        "海尔冰箱BCD-600WGHSS19B8U1的容量是多少",
        "SK-II神仙水精华液适合什么肤质"
    ],
    IntentType.ORDER: [
        "我的订单到哪了",
        "什么时候发货",
        "物流信息查询",
        "快递到哪了",
        "我的包裹什么时候到",
        "订单状态是什么",
        "配送时间是多少",
        "运单号是多少",
        "已经签收了吗",
        "发货了吗",
        "北京地区的配送时效是多久",
        "全场满多少元包邮",
        "如何查询物流信息",
        "大家电商品支持上门安装吗",
        "物流延迟了怎么办"
    ],
    IntentType.POLICY: [
        "能退货吗",
        "怎么保修",
        "退款流程是什么",
        "可以换货吗",
        "售后政策是什么",
        "质量问题怎么处理",
        "维修怎么弄",
        "退换货规则是什么",
        "保修期多久",
        "不满意可以退吗",
        "支持7天无理由退换货吗",
        "手机的保修期是多久",
        "如何联系客服申请售后",
        "质量问题可以退换货吗",
        "哪些商品不支持无理由退换货"
    ],
    IntentType.PROMOTION: [
        "有优惠吗",
        "满减活动是什么",
        "优惠券怎么用",
        "有什么折扣",
        "促销活动有哪些",
        "特价商品有哪些",
        "秒杀什么时候开始",
        "能便宜点吗",
        "有什么福利",
        "新人有什么优惠",
        "618大促有什么活动",
        "以旧换新服务怎么使用",
        "会员日有什么专属优惠",
        "如何获取和使用优惠券"
    ],
    IntentType.MEMBER: [
        "会员有什么等级",
        "积分怎么用",
        "会员权益有哪些",
        "怎么升级会员",
        "银卡会员有什么特权",
        "金卡会员有什么权益",
        "钻石会员有什么福利",
        "积分怎么兑换",
        "会员日有什么活动",
        "专属客服怎么联系",
        "钻石会员享受哪些专属权益",
        "积分有效期是多久",
        "企业批量采购有什么优惠政策"
    ],
    IntentType.PAYMENT: [
        "支持哪些支付方式",
        "可以开具增值税专用发票吗",
        "电子发票会发送到哪里",
        "支持花呗分期付款吗",
        "花呗分期12期利息多少",
        "对公转账流程是什么",
        "发票信息填错了怎么办",
        "价格保护政策是什么",
        "商品降价了可以补差价吗",
        "企业采购可以批量开票吗"
    ],
    IntentType.TECHNICAL: [
        "iPhone省电设置有哪些",
        "华为手机卫星通话功能怎么用",
        "MacBook新手入门指南",
        "大家电安装注意事项",
        "护肤品使用顺序是什么",
        "数码产品保养建议",
        "洗衣机洗涤程序怎么选择",
        "如何连接蓝牙耳机",
        "APP版本更新后有什么新功能"
    ]
}

_intent_embeddings: Dict[IntentType, np.ndarray] = {}
_intent_example_embeddings: Dict[IntentType, List[np.ndarray]] = {}
_embedding_service = None
_use_embedding = True


def _get_embedding_service():
    global _embedding_service
    if _embedding_service is None:
        from app.services.embedding_service import embedding_service
        _embedding_service = embedding_service
    return _embedding_service


def _cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return float(dot_product / (norm1 * norm2))


def _init_intent_embeddings():
    global _intent_embeddings, _intent_example_embeddings, _use_embedding
    
    if not _use_embedding:
        return False
    
    if _intent_embeddings:
        return True
    
    try:
        embedding_service = _get_embedding_service()
        
        for intent_type, examples in INTENT_EXAMPLES.items():
            embeddings = embedding_service.encode(examples)
            _intent_example_embeddings[intent_type] = [np.array(emb) for emb in embeddings]
            
            avg_embedding = np.mean(embeddings, axis=0)
            _intent_embeddings[intent_type] = avg_embedding / np.linalg.norm(avg_embedding)
        
        logger.info(f"[意图分类] Embedding 意图模板初始化完成，共 {len(_intent_embeddings)} 个意图类型")
        return True
    except Exception as e:
        logger.warning(f"[意图分类] Embedding 初始化失败，将使用关键词匹配: {e}")
        _use_embedding = False
        return False


def _classify_by_embedding(query: str) -> Optional[IntentResult]:
    if not _use_embedding:
        return None
    
    try:
        if not _init_intent_embeddings():
            return None
        
        embedding_service = _get_embedding_service()
        query_embedding = np.array(embedding_service.encode_single(query))
        
        intent_scores: Dict[IntentType, float] = {}
        intent_details: Dict[IntentType, Dict] = {}
        
        for intent_type, avg_emb in _intent_embeddings.items():
            avg_similarity = _cosine_similarity(query_embedding, avg_emb)
            
            example_embeddings = _intent_example_embeddings.get(intent_type, [])
            max_similarity = 0.0
            best_example_idx = -1
            
            for idx, example_emb in enumerate(example_embeddings):
                sim = _cosine_similarity(query_embedding, example_emb)
                if sim > max_similarity:
                    max_similarity = sim
                    best_example_idx = idx
            
            final_score = 0.4 * avg_similarity + 0.6 * max_similarity
            intent_scores[intent_type] = final_score
            intent_details[intent_type] = {
                "avg_similarity": avg_similarity,
                "max_similarity": max_similarity,
                "best_example_idx": best_example_idx
            }
        
        best_intent = max(intent_scores, key=intent_scores.get)
        best_score = intent_scores[best_intent]
        
        details = intent_details[best_intent]
        best_example = INTENT_EXAMPLES[best_intent][details["best_example_idx"]]
        
        return IntentResult(
            intent=best_intent,
            confidence=min(best_score, 0.95),
            matched_keywords=[f"相似示例: {best_example}"],
            reasoning=f"Embedding相似度: avg={details['avg_similarity']:.3f}, max={details['max_similarity']:.3f}"
        )
        
    except Exception as e:
        logger.warning(f"[意图分类] Embedding 分类失败: {e}")
        return None


def _classify_by_keywords(query: str) -> IntentResult:
    for intent_type, keywords in INTENT_KEYWORDS.items():
        for kw in keywords:
            if kw in query:
                logger.info(f"[意图分类] 匹配关键词 '{kw}' -> {intent_type.value}")
                return IntentResult(
                    intent=intent_type,
                    confidence=0.8,
                    matched_keywords=[kw],
                    reasoning=f"匹配关键词: {kw}"
                )
    
    return IntentResult(
        intent=IntentType.PRODUCT,
        confidence=0.5,
        matched_keywords=[],
        reasoning="无匹配关键词，默认商品咨询"
    )


def classify_intent(query: str) -> IntentResult:
    if not query or not query.strip():
        return IntentResult(
            intent=IntentType.PRODUCT,
            confidence=0.5,
            matched_keywords=[],
            reasoning="空查询"
        )
    
    query = query.strip()
    
    if ORDER_PATTERN.search(query):
        logger.info(f"[意图分类] 检测到订单号: {query}")
        return IntentResult(
            intent=IntentType.ORDER,
            confidence=0.95,
            matched_keywords=["订单号"],
            reasoning="匹配订单号格式"
        )
    
    embedding_result = _classify_by_embedding(query)
    if embedding_result and embedding_result.confidence >= 0.6:
        logger.info(f"[意图分类] Embedding 分类结果: {embedding_result.intent.value} (置信度: {embedding_result.confidence:.3f})")
        return embedding_result
    
    keyword_result = _classify_by_keywords(query)
    logger.info(f"[意图分类] 关键词分类结果: {keyword_result.intent.value} (置信度: {keyword_result.confidence:.3f})")
    
    if embedding_result:
        if embedding_result.confidence > keyword_result.confidence:
            logger.info(f"[意图分类] 采用 Embedding 结果 (更高置信度)")
            return embedding_result
    
    return keyword_result


def preload_intent_embeddings():
    """预加载意图 Embedding 模板"""
    logger.info("[意图分类] 开始预加载意图 Embedding...")
    success = _init_intent_embeddings()
    if success:
        logger.info("[意图分类] 意图 Embedding 预加载完成")
    else:
        logger.warning("[意图分类] 意图 Embedding 预加载失败，将使用关键词匹配")
    return success


intent_classifier = type('IntentClassifier', (), {
    'classify': staticmethod(classify_intent),
    'is_low_confidence': staticmethod(lambda c: c < 0.6),
    'preload': staticmethod(preload_intent_embeddings)
})()
