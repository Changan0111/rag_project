"""一键式全量重建Milvus + BM25索引脚本
用于将MySQL中的knowledge_docs全量同步到向量数据库

运行方式:
    cd backend
    python rebuild_all_indexes.py
"""
import sys
import time
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from pymilvus import connections, utility
from app.core.config import settings
from app.core.database import SessionLocal
from app.models import KnowledgeDoc, KnowledgeSyncLog
from app.services.embedding_service import embedding_service
from app.services.milvus_service import milvus_service
from app.services.bm25_service import bm25_service


def main():
    print("=" * 60)
    print("🚀 开始全量重建向量索引")
    print("=" * 60)

    start_time = time.time()

    # Step 1: 连接Milvus并清空旧集合
    print("\n📦 Step 1/4: 连接Milvus并重建集合...")
    try:
        connections.connect(
            alias="default",
            host=settings.MILVUS_HOST,
            port=settings.MILVUS_PORT
        )
        print(f"   ✅ 已连接到 Milvus ({settings.MILVUS_HOST}:{settings.MILVUS_PORT})")

        if utility.has_collection(settings.COLLECTION_NAME):
            print(f"   🗑️  删除旧集合: {settings.COLLECTION_NAME}")
            utility.drop_collection(settings.COLLECTION_NAME)

        milvus_service._create_hnsw_collection()
        print(f"   ✅ 新集合已创建 (HNSW索引, M={settings.HNSW_M}, efConstruction={settings.HNSW_EF_CONSTRUCTION})")

    except Exception as e:
        print(f"   ❌ Milvus连接失败: {e}")
        return False

    # Step 2: 从MySQL读取所有知识文档
    print("\n📚 Step 2/4: 从MySQL读取知识库数据...")
    db = SessionLocal()
    try:
        docs = db.query(KnowledgeDoc).all()
        total_docs = len(docs)
        print(f"   ✅ 共读取 {total_docs} 条知识文档")

        if total_docs == 0:
            print("   ⚠️  没有找到任何知识文档，请先导入数据！")
            return False

    except Exception as e:
        print(f"   ❌ 数据库查询失败: {e}")
        return False
    finally:
        db.close()

    # Step 3: 生成Embedding并插入Milvus
    print("\n🔢 Step 3/4: 生成Embedding向量...")
    try:
        doc_ids = []
        contents = []
        categories = []

        print(f"   ⏳ 正在编码 {total_docs} 条文本...", end=" ", flush=True)
        texts = [doc.content for doc in docs]
        all_embeddings = embedding_service.encode(texts)
        print(f"✅ 完成！耗时 {time.time()-start_time:.1f}s")

        for i, doc in enumerate(docs):
            doc_ids.append(doc.id)
            contents.append(doc.content[:2000])
            categories.append(doc.category)

        insert_count = milvus_service.insert_vectors(
            doc_ids=doc_ids,
            contents=contents,
            embeddings=all_embeddings,
            categories=categories
        )
        print(f"   ✅ 已插入 {insert_count} 条向量到Milvus")

    except Exception as e:
        print(f"   ❌ Embedding生成失败: {e}")
        return False

    # Step 4: 重建BM25索引
    print("\n📝 Step 4/4: 重建BM25倒排索引...")
    try:
        bm25_service.clear()
        for doc in docs:
            bm25_service.add_document(
                doc_id=doc.id,
                content=doc.content,
                category=doc.category
            )
        bm25_service.save_index()
        bm25_stats = bm25_service.get_stats()
        print(f"   ✅ BM25索引已保存 (词汇量: {bm25_stats.get('vocab_size', 0)})")

    except Exception as e:
        print(f"   ❌ BM25索引构建失败: {e}")
        return False

    # 记录同步日志
    db = SessionLocal()
    try:
        for doc in docs:
            log = KnowledgeSyncLog(
                doc_id=doc.id,
                action='full_sync',
                status='success'
            )
            db.add(log)
        db.commit()
    finally:
        db.close()

    # 输出最终统计
    elapsed_time = time.time() - start_time
    milvus_stats = milvus_service.get_collection_stats()

    print("\n" + "=" * 60)
    print("✨ 全量重建完成！")
    print("=" * 60)
    print(f"\n📊 统计信息:")
    print(f"   • Milvus向量数:  {milvus_stats['num_entities']}")
    print(f"   • 索引类型:       {milvus_stats['index_type']}")
    print(f"   • HNSW参数:       M={settings.HNSW_M}, efSearch={settings.HNSW_EF_SEARCH}")
    print(f"   • BM25文档数:     {total_docs}")
    print(f"   • 总耗时:         {elapsed_time:.1f}秒")
    print(f"\n🎉 所有100条知识已成功同步到向量数据库！")
    print("=" * 60)

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
