"""
📋 应用配置文件 (config.py)
============================
本文件定义了所有配置项的默认值、类型和验证逻辑。
优先级：.env 文件 > 系统环境变量 > 此处的默认值

使用方法：
    from app.core.config import settings
    print(settings.DATABASE_URL)
"""

from pydantic_settings import BaseSettings
from functools import lru_cache
import os
import secrets


class Settings(BaseSettings):
    
    # ============================================
    # 🗄️ 数据库配置
    # ============================================
    DATABASE_URL: str = "mysql+pymysql://root:123456@localhost:3306/rag_ecommerce"
    """MySQL 数据库连接字符串（包含用户名密码）"""
    
    @property
    def SECRET_KEY(self) -> str:
        """
        🔐 JWT 密钥（自动生成或从环境变量读取）
        
        优先级：
        1. 环境变量 SECRET_KEY
        2. .secret_key 文件内容
        3. 自动生成并保存到 .secret_key 文件
        
        ⚠️ 生产环境请务必设置强密钥！
        """
        key = os.getenv("SECRET_KEY")
        if key and key != "your-secret-key-change-in-production":
            return key
        
        key_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
            ".secret_key"
        )
        if os.path.exists(key_file):
            with open(key_file, "r") as f:
                return f.read().strip()
        
        new_key = secrets.token_urlsafe(32)
        try:
            with open(key_file, "w") as f:
                f.write(new_key)
        except Exception:
            pass
        return new_key
    
    ALGORITHM: str = "HS256"
    """JWT 签名算法（固定为 HS256）"""
    
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    """Token 有效期（分钟），默认 24 小时"""
    
    # ============================================
    # 🗄️ Milvus 向量数据库配置
    # ============================================
    MILVUS_HOST: str = "localhost"
    """Milvus 服务地址"""
    
    MILVUS_PORT: int = 19530
    """Milvus 服务端口"""
    
    # ============================================
    # 🤖 LLM 大语言模型配置 (Ollama)
    # ============================================
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    """Ollama API 地址（本地部署的 LLM 服务）"""
    
    OLLAMA_MODEL: str = "qwen2.5:3b"
    """使用的模型名称（可通过 .env 切换其他模型）"""
    
    # ============================================
    # 📊 Embedding 向量模型配置
    # ============================================
    EMBEDDING_MODEL: str = "BAAI/bge-large-zh"
    """
    Embedding 模型名称
    - bge-large-zh: 中文大模型（1024维，效果好）
    - bge-base-zh: 中文基础模型（768维，速度快）
    """
    
    EMBEDDING_DIMENSION: int = 1024
    """向量维度（必须与模型匹配，不可随意修改）"""
    
    EMBEDDING_BATCH_SIZE: int = 32
    """批量处理大小（影响内存占用和速度）"""
    
    EMBEDDING_NUM_WORKERS: int = 1
    """并行工作线程数（CPU 推理时建议=1 避免资源竞争）"""
    
    EMBEDDING_MAX_TOKENS: int = 256
    """
    最大 Token 数（文本截断长度）
    - 256: 标准长度（适合短文本）
    - 512: 长文本（适合文档段落）
    💡 越长越准确但越慢
    """
    
    # ============================================
    # 📚 Milvus 集合配置
    # ============================================
    COLLECTION_NAME: str = "knowledge_vectors"
    """Milvus 集合名称（知识库向量存储表）"""
    
    AUTO_BOOTSTRAP_KNOWLEDGE_INDEXES: bool = True
    """是否在启动时自动构建索引（首次部署建议开启）"""
    
    AUTO_BOOTSTRAP_KNOWLEDGE_INDEXES_MODE: str = "if_empty"
    """
    自动构建模式：
    - 'if_empty': 仅当集合为空时构建（推荐）
    - 'always': 每次启动都重建（调试用）
    - 'never': 从不自动构建
    """
    
    # ============================================
    # 🔄 Redis 缓存配置
    # ============================================
    REDIS_HOST: str = "localhost"
    """Redis 服务地址"""
    
    REDIS_PORT: int = 6379
    """Redis 服务端口"""
    
    REDIS_DB: int = 0
    """Redis 数据库编号（0-15）"""
    
    REDIS_PASSWORD: str = ""
    """Redis 密码（空表示无密码）"""
    
    CACHE_ENABLED: bool = True
    """是否启用语义缓存（相似问题直接返回缓存答案）"""
    
    CACHE_TTL: int = 3600
    """缓存过期时间（秒），默认 1 小时"""
    
    CACHE_SIMILARITY_THRESHOLD: float = 0.95
    """
    缓存命中阈值（余弦相似度）
    - 0.95: 高精度（几乎完全相同才命中缓存）
    - 0.90: 中等精度
    - 0.85: 宽松匹配
    """
    
    # ============================================
    # 📁 文件上传配置
    # ============================================
    UPLOAD_DIR: str = "uploads"
    """上传文件存储目录（相对于项目根目录）"""
    
    MAX_FILE_SIZE: int = 5 * 1024 * 1024
    """最大文件大小（字节），默认 5MB"""
    
    # ============================================
    # 🎯 Milvus HNSW 索引参数（高级调优）
    # ============================================
    HNSW_M: int = 16
    """
    HNSW 图的连接数（影响召回率和内存）
    - 8-16: 平衡模式（推荐）
    - 32-64: 高召回率（内存消耗大）
    """
    
    HNSW_EF_CONSTRUCTION: int = 200
    """
    构建索引时的搜索范围（影响构建速度和质量）
    - 100-200: 快速构建
    - 200-400: 高质量构建（推荐）
    """
    
    HNSW_EF_SEARCH: int = 48
    """
    查询时的搜索范围（影响查询速度和召回率）
    - 32-64: 平衡模式（推荐）
    - 100+: 高召回率（慢）
    """
    
    # ============================================
    # 🔍 Rerank 重排序模型配置
    # ============================================
    RERANK_MODEL: str = "BAAI/bge-reranker-base"
    """
    重排序模型名称（用于对检索结果重新排序以提升质量）
    - bge-reranker-base: ~400MB, ~80ms/批（推荐✅ 平衡之选）
    - bge-reranker-large: ~1.2GB, ~200ms/批（高质量但慢）
    """
    
    RERANK_ENABLED: bool = True
    """是否启用重排序功能（关闭则只使用 RRF 混合检索）"""
    
    RERANK_CANDIDATE_MULTIPLIER: int = 2
    """
    候选文档倍数（top_k × multiplier = 实际检索数量）
    - 1.5: 追求速度
    - 2: 平衡性能（推荐✅）
    - 3: 追求质量
    """
    
    RETRIEVAL_TOP_K: int = 5
    """
    最终返回给 LLM 的参考文档数量
    - 3-4: 精简回答（Token 少，响应快）
    - 5-6: 全面回答（推荐✅）
    - 8-10: 详细回答（Token 多）
    """
    
    # ============================================
    # ⚡ GPU/CPU 资源分配策略
    # ============================================
    FORCE_EMBEDDING_CPU: bool = True
    """
    强制 Embedding 模型使用 CPU（不占用 GPU 显存）
    ✅ 推荐：GPU 显存留给 LLM 使用
    
    设为 False 时：Embedding 会尝试使用 GPU（需要足够显存）
    """
    
    FORCE_RERANK_CPU: bool = True
    """
    强制 Rerank 模型使用 CPU（不占用 GPU 显存）
    ✅ 推荐：GPU 显存留给 LLM 使用
    
    设为 False 时：Rerank 会尝试使用 GPU（需要额外显存）
    """
    
    USE_GPU: bool = False
    """
    全局 GPU 开关（影响 Milvus 等组件）
    ⚠️ 注意：即使此处为 True，
       FORCE_EMBEDDING_CPU 和 FORCE_RERANK_CPU 
       仍然可以强制对应模型使用 CPU！
    
    建议配置：
    - False: 全部 CPU（适合显存不足或无独立显卡）
    - True: GPU 可用（需确保有足够显存）
    """
    
    # ============================================
    # 🌐 CORS 跨域配置
    # ============================================
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173"
    """
    允许的前端地址（多个用逗号分隔）
    开发环境通常包括：
    - Vite 开发服务器 (5173)
    - React 开发服务器 (3000)
    """

    class Config:
        env_file = ".env"
        """Pydantic Settings 配置文件路径"""
        extra = "ignore"
        """忽略 .env 中未定义的配置项（避免报错）"""


@lru_cache()
def get_settings() -> Settings:
    """
    获取全局配置实例（单例模式，带缓存）
    
    使用示例：
        from app.core.config import get_settings
        settings = get_settings()
        print(settings.DATABASE_URL)
    """
    return Settings()


# 全局配置实例（整个应用共享）
settings = get_settings()

# 项目根目录路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 上传文件完整路径
UPLOAD_PATH = os.path.join(BASE_DIR, settings.UPLOAD_DIR)

# 创建必要的目录
os.makedirs(UPLOAD_PATH, exist_ok=True)
os.makedirs(os.path.join(UPLOAD_PATH, "avatars"), exist_ok=True)
