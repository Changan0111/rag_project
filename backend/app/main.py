from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import logging

from app.api.routers import api_router
from app.services.milvus_service import milvus_service
from app.services.embedding_service import embedding_service
from app.services.llm_service import LLMService
from app.services.knowledge_sync_service import setup_knowledge_events
from app.services.index_bootstrap_service import index_bootstrap_service
from app.services.redis_service import redis_service
from app.services.rerank_service import rerank_service
from app.services.intent_classifier import intent_classifier
from app.core.config import UPLOAD_PATH, settings
from app.core.database import Base, engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up...")

    Base.metadata.create_all(bind=engine)
    logger.info("Database tables ensured")
    
    app.state.llm_service = LLMService()
    logger.info("LLMService initialized")
    
    try:
        milvus_service.connect()
        milvus_service.create_collection()
        logger.info("Milvus connection established")
    except Exception as e:
        logger.warning(f"Milvus connection failed: {e}")
    
    try:
        embedding_service.load_model()
        logger.info("Embedding model loaded")
    except Exception as e:
        logger.warning(f"Embedding model loading failed: {e}")

    try:
        intent_classifier.preload()
        logger.info("Intent classifier embeddings preloaded")
    except Exception as e:
        logger.warning(f"Intent classifier preload failed: {e}")

    try:
        logger.info(f"Checking rerank service... enabled={rerank_service.is_enabled()}, model_name={settings.RERANK_MODEL}")
        if rerank_service.is_enabled():
            logger.info(f"Loading rerank model: {settings.RERANK_MODEL}...")
            rerank_service.load_model()
            logger.info("✅ Rerank model preloaded successfully")
        else:
            logger.info("⚠️ Rerank service is disabled, skipping preload")
    except Exception as e:
        import traceback
        logger.error(f"❌ Rerank model preloading failed:\n{traceback.format_exc()}")

    try:
        redis_service.connect()
        logger.info("Redis cache service initialized")
    except Exception as e:
        logger.warning(f"Redis connection failed: {e}")

    try:
        setup_knowledge_events()
        logger.info("Knowledge auto-sync events registered")
    except Exception as e:
        logger.warning(f"Knowledge events setup failed: {e}")

    # 启动时可选自动初始化知识库索引（可通过配置开关关闭）
    if settings.AUTO_BOOTSTRAP_KNOWLEDGE_INDEXES:
        try:
            doc_count, inserted_count = index_bootstrap_service.bootstrap_knowledge_indexes(
                mode=settings.AUTO_BOOTSTRAP_KNOWLEDGE_INDEXES_MODE
            )
            logger.info(
                "Knowledge indexes bootstrapped: mode=%s, docs=%s, milvus_inserted=%s",
                settings.AUTO_BOOTSTRAP_KNOWLEDGE_INDEXES_MODE,
                doc_count,
                inserted_count
            )
        except Exception as e:
            logger.warning(f"Knowledge index bootstrap failed: {e}")
    else:
        logger.info("Skip knowledge index bootstrap (AUTO_BOOTSTRAP_KNOWLEDGE_INDEXES=false)")
    
    yield
    
    logger.info("Shutting down...")
    
    try:
        redis_service.close()
        logger.info("Redis connection closed")
    except Exception as e:
        logger.warning(f"Redis closing failed: {e}")
    
    try:
        await app.state.llm_service.close()
        logger.info("LLM service closed")
    except Exception as e:
        logger.warning(f"LLM service closing failed: {e}")


app = FastAPI(
    title="RAG电商智能客服系统",
    description="基于RAG技术的电商智能客服系统API",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory=UPLOAD_PATH), name="uploads")

app.include_router(api_router, prefix="/api")


@app.get("/")
def root():
    return {"message": "RAG电商智能客服系统API", "version": "1.0.0"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
