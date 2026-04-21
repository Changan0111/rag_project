# RAG电商智能客服机器人

一个基于\*\*检索增强生成（Retrieval-Augmented Generation, RAG）\*\*技术的电商智能客服系统。通过结合大语言模型（LLM）、向量数据库（Milvus）和混合检索引擎（向量+BM25+RRF融合+重排序），为电商场景提供智能对话、订单查询、知识库管理和人工客服转接等一站式解决方案。

***

## 核心特性

| 特性        | 说明                                                          |
| --------- | ----------------------------------------------------------- |
| **智能对话**  | 流式打字机效果输出，支持多轮上下文记忆，首token延迟<1秒                             |
| **混合检索**  | 向量语义检索（Milvus HNSW）+ BM25关键词检索 + RRF排序融合 + Cross-Encoder重排序 |
| **知识库管理** | 管理员可创建/编辑/删除知识文档，自动切分文本并向量化，支持增量同步到向量数据库                    |
| **意图识别**  | 关键词快速匹配（第一层）+ 语义相似度计算（第二层），低置信度自动转人工                        |
| **语义缓存**  | 基于Redis的向量相似度缓存，余弦相似度≥0.95直接返回历史答案，大幅提升响应速度                 |
| **人工客服**  | 意图识别失败或用户主动请求时转接，管理员后台接单、实时回复、关单                            |
| **评估中心**  | 内置RAG评估体系，支持忠实度、答案相关性、上下文精确度多维度评测，支持召回对比实验                  |
| **数据仪表盘** | 用户活跃度、对话量趋势、热门问题TOP10（语义聚类）、今日对话实时统计                        |

***

## 系统架构

```
┌───────────────────────────────────────────────────────────────┐
│                         用户界面层                              │
│                    Vue 3 + Element Plus                        │
└───────────────────────────────┬───────────────────────────────┘
                                │ HTTP / SSE
┌───────────────────────────────▼───────────────────────────────┐
│                         API网关层                              │
│                  FastAPI (RESTful + SSE)                       │
│            JWT认证 · CORS · 请求验证 · 异常处理                │
└──┬────────────┬────────────┬──────────────┬──────────────┬────┘
   │            │            │              │              │
   ▼            ▼            ▼              ▼              ▼
┌──────┐  ┌──────────┐  ┌──────┐  ┌──────────┐  ┌──────────┐
│ RAG  │  │ 意图分类  │  │ 订单  │  │ 人工客服  │  │ 评估中心  │
│ 流程  │  │          │  │ 查询  │  │ 工单管理  │  │ 评测统计  │
└──┬───┘  └──────────┘  └──┬───┘  └────┬─────┘  └──────────┘
   │                        │            │
   ▼                        ▼            ▼
┌───────────────────────────────────────────────────────┐
│                    数据存储层                           │
│                                                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐       │
│  │ MySQL    │  │ Milvus   │  │ Redis        │       │
│  │ 8.0+     │  │ 2.x(HNSW)│  │ 7.x          │       │
│  │ 用户/订单 │  │ 向量索引  │  │ 语义缓存     │       │
│  │ 知识库    │  │          │  │ 会话缓存     │       │
│  └──────────┘  └──────────┘  └──────────────┘       │
└───────────────────────────────────────────────────────┘
                                                       │
┌──────────────────────────────────────────────────────┐
│                    AI 推理层                           │
│                                                      │
│  ┌──────────────┐  ┌──────────────┐                  │
│  │ Ollama       │  │ PyTorch      │                  │
│  │ Qwen2.5:3B   │  │ BGE-Large-ZH │                  │
│  │ 生成回答     │  │ 向量编码      │                  │
│  └──────────────┘  └──────────────┘                  │
│                                                      │
│  ┌──────────────────┐  ┌──────────────┐             │
│  │ BM25 (自实现)    │  │ BGE-Reranker  │             │
│  │ 关键词检索       │  │ Cross-Encoder │             │
│  └──────────────────┘  └──────────────┘             │
└──────────────────────────────────────────────────────┘
```

***

## RAG核心流程

```
用户提问
    │
    ▼
┌─────────────┐
│ 敏感词过滤   │ ──── 命中 → 拒绝回答
└──────┬──────┘
       ▼
┌─────────────┐
│ 意图识别     │ ──── 订单类 → 解析订单号 → 查询MySQL
└──────┬──────┘
       ▼
┌─────────────┐
│ 语义缓存     │ ──── 相似度≥0.95 → 直接返回缓存答案
└──────┬──────┘
       ▼
┌─────────────────────┐
│    混合检索引擎       │
│  ┌───────┐ ┌───────┐ │
│  │向量检索│ │BM25检索│ │  并行执行
│  │Milvus │ │Jieba  │ │
│  └───┬───┘ └───┬───┘ │
│      └───┬─────┘     │
│          ▼           │
│    RRF融合排序         │
│          ▼           │
│  [可选] Cross-Encoder │  重排序提升精度
└──────┬───────────────┘
       ▼
┌─────────────┐
│ 构建Prompt   │  历史对话 + 检索到的知识片段
└──────┬──────┘
       ▼
┌─────────────┐
│ LLM生成回答  │  Ollama Qwen2.5:3B 流式输出
└──────┬──────┘
       ▼
┌─────────────┐
│ 保存缓存+历史 │  存入Redis + MySQL
└─────────────┘
```

***

## 技术栈

### 前端

| 技术           | 版本    | 用途                    |
| ------------ | ----- | --------------------- |
| Vue 3        | 3.4+  | 前端框架（Composition API） |
| Vite         | 5.0+  | 构建工具（HMR热更新）          |
| Pinia        | 2.1+  | 状态管理（用户/对话/会话）        |
| Vue Router   | 4.2+  | 路由管理                  |
| Element Plus | 2.4+  | UI组件库                 |
| Axios        | 1.6+  | HTTP请求封装              |
| markdown-it  | 14.1+ | Markdown渲染（对话输出）      |

### 后端

| 技术          | 版本     | 用途                     |
| ----------- | ------ | ---------------------- |
| FastAPI     | 0.109+ | 异步Web框架（自动生成OpenAPI文档） |
| SQLAlchemy  | 2.0+   | ORM框架                  |
| Pydantic    | 2.5+   | 数据验证与序列化               |
| PyMySQL     | 1.1+   | MySQL驱动                |
| Uvicorn     | 0.27+  | ASGI服务器                |
| Python-JOSE | 3.3+   | JWT令牌处理                |
| Passlib     | 1.7+   | 密码哈希（bcrypt）           |

### AI/数据层

| 技术                     | 版本      | 用途            |
| ---------------------- | ------- | ------------- |
| Ollama                 | 最新      | 本地LLM推理服务     |
| Qwen2.5:3B             | 30亿参数   | 阿里通义千问开源模型    |
| Milvus                 | 2.3+    | 向量数据库（HNSW索引） |
| BAAI/bge-large-zh      | 1024维   | 中文文本向量化模型     |
| BAAI/bge-reranker-base | \~400MB | 交叉编码器重排序      |
| Redis                  | 7.x     | 语义缓存 + 会话缓存   |
| Jieba                  | 0.42+   | 中文分词（BM25）    |
| LangChain              | 0.0.38+ | 文本切分工具        |
| PyTorch                | 2.7+    | 深度学习推理框架      |
| Sentence-Transformers  | 2.3+    | 句子嵌入模型库       |

***

## 项目结构

```
├── backend/                          # Python 后端
│   ├── app/
│   │   ├── api/
│   │   │   ├── routers/              # API路由模块
│   │   │   │   ├── auth.py           # 认证（注册/登录/头像/密码）
│   │   │   │   ├── chat.py           # 对话（同步/流式/历史/会话）
│   │   │   │   ├── knowledge.py      # 知识库（CRUD/同步到向量库）
│   │   │   │   ├── orders.py         # 订单（列表/详情/物流）
│   │   │   │   ├── tickets.py        # 人工客服（工单管理）
│   │   │   │   ├── evaluation.py     # 评估（单条/批量/数据集/召回对比）
│   │   │   │   └── stats.py          # 统计（仪表盘/缓存/BM25/日志）
│   │   │   └── dependencies.py       # FastAPI依赖注入
│   │   ├── core/
│   │   │   ├── config.py             # 全局配置（环境变量读取）
│   │   │   ├── database.py           # MySQL连接管理
│   │   │   └── security.py           # JWT/密码工具
│   │   ├── models/
│   │   │   └── models.py             # SQLAlchemy ORM（12张表）
│   │   ├── schemas/
│   │   │   └── schemas.py            # Pydantic请求/响应模型
│   │   ├── services/                 # 业务逻辑层（核心）
│   │   │   ├── rag_service.py        # RAG流程编排（主引擎）
│   │   │   ├── llm_service.py        # Ollama HTTP调用
│   │   │   ├── embedding_service.py  # BGE向量化编码
│   │   │   ├── milvus_service.py     # Milvus向量库操作
│   │   │   ├── bm25_service.py       # BM25关键词检索
│   │   │   ├── hybrid_search_service.py  # 混合检索（RRF融合）
│   │   │   ├── rerank_service.py     # Cross-Encoder重排序
│   │   │   ├── intent_classifier.py  # 意图分类
│   │   │   ├── semantic_cache_service.py # Redis语义缓存
│   │   │   ├── sensitive_service.py  # 敏感词过滤
│   │   │   ├── human_service.py      # 人工客服转接
│   │   │   ├── knowledge_sync_service.py # 知识库增量同步
│   │   │   ├── index_bootstrap_service.py# 启动时索引初始化
│   │   │   └── evaluation_service.py # RAG评估（忠实度/相关性）
│   │   └── utils/
│   │       └── text_chunker.py       # 文本切分（LangChain切分器）
│   ├── data/
│   │   └── bm25_index.pkl            # BM25索引持久化
│   ├── .env.example                  # 环境变量模板（提交Git）
│   ├── requirements.txt              # Python依赖清单
│   ├── rebuild_all_indexes.py        # 全量重建索引脚本
│   └── run.py                        # 启动入口
├── frontend/                         # Vue 3 前端
│   ├── src/
│   │   ├── api/                      # Axios API封装
│   │   │   ├── index.js              # Axios实例配置（拦截器/错误处理）
│   │   │   └── modules.js            # 各模块API方法
│   │   ├── router/
│   │   │   └── index.js              # 路由定义 + 权限守卫
│   │   ├── stores/                   # Pinia状态管理
│   │   │   ├── user.js               # 用户信息
│   │   │   ├── chat.js               # 对话状态
│   │   │   └── session.js            # 会话列表
│   │   ├── styles/
│   │   │   └── main.scss             # 全局样式
│   │   ├── layouts/
│   │   │   └── MainLayout.vue        # 主布局（侧边栏+顶栏）
│   │   └── views/                    # 页面组件
│   │       ├── Login.vue             # 登录页
│   │       ├── chat.vue              # 智能对话（流式输出+Markdown渲染）
│   │       ├── Dashboard.vue         # 数据仪表盘
│   │       ├── orders.vue            # 订单查询
│   │       ├── Knowledge.vue         # 知识库管理
│   │       ├── ServiceDesk.vue       # 人工客服台
│   │       ├── BuiltinEvaluation.vue # 评估中心
│   │       ├── RecallComparison.vue  # 召回对比实验
│   │       ├── CacheManage.vue       # 缓存管理
│   │       ├── ChatLogs.vue          # 对话日志
│   │       └── Profile.vue           # 个人中心
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
├── docker-compose.yml                # Milvus + Redis 容器编排
└── README.md
```

***

## 数据库设计

系统共包含 **12张表**，核心关系如下：

```
User (1) ── (N) Order ── (N) OrderItem
  │                         │
  │                    (1) Logistics ── (N) LogisticsTrack
  │
  ├── (N) ChatHistory          ← 对话消息（含来源引用）
  ├── (N) HumanServiceSession  ← 人工工单（含排队状态）
  └── (N) EvaluationRecord     ← 评估记录
       │
       └── EvaluationDataset   ← 评估测试集
```

| 表名                       | 说明                                                        |
| ------------------------ | --------------------------------------------------------- |
| `users`                  | 用户表（username/password/phone/role/avatar）                  |
| `products`               | 商品表（name/category/price/specs/stock）                      |
| `orders`                 | 订单表（order\_no/status/total\_amount/payment\_method）       |
| `order_items`            | 订单项表                                                      |
| `logistics`              | 物流表（tracking\_no/carrier/status/current\_location）        |
| `logistics_tracks`       | 物流轨迹表                                                     |
| `chat_history`           | 对话历史表（session\_id/role/content/source/reference\_sources） |
| `human_service_sessions` | 人工工单表（status/transfer\_reason/assigned\_admin\_id）        |
| `knowledge_docs`         | 知识文档表（title/content/category/source）                      |
| `knowledge_sync_logs`    | 同步日志表                                                     |
| `evaluation_records`     | 评估记录表                                                     |
| `evaluation_dataset`     | 评估数据集表（含question\_embedding）                              |

***

## 快速部署

### 前置要求

- **Python** 3.10+
- **Node.js** 18+
- **MySQL** 8.0+
- **Docker + Docker Compose**

### 1. 创建 MySQL 数据库

```sql
CREATE DATABASE rag_ecommerce CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 2. 启动基础设施（Milvus + Redis）

```bash
docker-compose up -d
```

该命令会启动以下容器：

- `milvus-etcd`：Milvus元数据存储
- `milvus-minio`：Milvus对象存储
- `milvus-standalone`：Milvus向量数据库（端口 19530）
- `redis`：Redis缓存服务（端口 6379）

### 3. 安装后端依赖

```bash
cd backend
pip install -r requirements.txt
```

### 4. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件，**至少修改以下项**：

```env
# MySQL 连接（必须修改为你的密码）
DATABASE_URL=mysql+pymysql://root:你的MySQL密码@localhost:3306/rag_ecommerce

# JWT 密钥（留空会自动生成，生产环境建议设置强密钥）
SECRET_KEY=your-secret-key-change-in-production
```

> **提示**：其他配置项均有合理的默认值，无需修改即可运行。

### 5. 安装并配置 Ollama

**安装 Ollama：**

```bash
# macOS / Linux
curl -fsSL https://ollama.com/install.sh | sh

# Windows: 从 https://ollama.com 下载安装包
```

**拉取模型（约2GB）：**

```bash
ollama pull qwen2.5:3b
```

模型会自动在本地启动（默认端口 `11434`），后端通过 HTTP 调用。

### 6. 启动后端服务

```bash
cd backend
python run.py
# 或 uvicorn app.main:app --reload --port 8000
```

启动时会自动：

- 创建数据库表（首次运行）
- 连接 Milvus 并创建向量集合
- 加载 Embedding 模型
- 加载 Rerank 模型（如启用）
- 连接 Redis
- 初始化知识库索引（如配置 `AUTO_BOOTSTRAP_KNOWLEDGE_INDEXES=true`）

启动成功后访问 `http://localhost:8000/docs` 可查看所有 API 接口。

### 7. 安装前端依赖并启动

```bash
cd ../frontend
npm install
npm run dev
```

访问 `http://localhost:5173` 即可使用系统。

### 8. 首次使用

1. 注册一个普通用户账号
2. 在 MySQL 中将某个用户的 `role` 改为 `admin` 以使用管理功能
3. 在"知识库管理"中添加知识文档
4. 点击"同步到向量库"按钮，系统会自动：
   - 将文本切分为多个片段（每段约200字符）
   - 使用 BGE 模型生成向量
   - 存储到 Milvus
   - 重建 BM25 索引
5. 回到对话页面开始测试

***

## 低配置部署建议

如果你使用的是 **8GB内存 / 无GPU** 的机器，以下是优化方案：

### 硬件消耗参考

| 组件                       | 内存占用        | 显存需求        |
| ------------------------ | ----------- | ----------- |
| Qwen2.5:3B (Ollama)      | \~2.5GB     | 无GPU时共享系统内存 |
| BGE-Large-ZH (Embedding) | \~1.5GB     | 默认CPU运行     |
| BGE-Reranker-Base        | \~800MB     | 默认CPU运行     |
| Milvus + Etcd + MinIO    | \~800MB     | -           |
| MySQL                    | \~200MB     | -           |
| Redis                    | \~100MB     | -           |
| **总计**                   | **\~5.9GB** | -           |

### 优化措施

#### 1. 关闭重排序（节省 \~800MB）

```env
RERANK_ENABLED=false
```

#### 2. 关闭语义缓存（节省 \~100MB + Redis开销）

```env
CACHE_ENABLED=false
```

#### 3. 减少返回文档数

```env
RETRIEVAL_TOP_K=3
```

#### 4. 使用更轻量的Embedding模型

```env
EMBEDDING_MODEL=BAAI/bge-base-zh-v1.5
EMBEDDING_DIMENSION=768
```

> 注意：修改维度后需清空 Milvus 重新同步知识库。

#### 5. 关闭Docker中的MinIO控制台

编辑 `docker-compose.yml`，移除 `9001:9001` 端口映射，减少资源占用。

### 最低可行配置

| 项目  | 要求                                                             |
| --- | -------------------------------------------------------------- |
| 内存  | 8GB（关闭重排序 + 关闭缓存后约需 5.1GB）                                     |
| CPU | 4核以上                                                           |
| GPU | 无需，纯CPU可运行（首答约3-8秒）                                            |
| 存储  | 预留 10GB（Ollama模型2.3GB + Embedding 1.5GB + Rerank 0.4GB + 数据空间） |

***

## 服务端口

| 服务          | 端口        | 说明                |
| ----------- | --------- | ----------------- |
| 前端（Vite）    | 5173      | 开发服务器             |
| 后端（FastAPI） | 8000      | API服务 + Swagger文档 |
| Ollama      | 11434     | LLM推理服务           |
| MySQL       | 3306      | 关系数据库             |
| Milvus      | 19530     | 向量数据库             |
| MinIO       | 9000/9001 | Milvus对象存储        |
| Etcd        | 2379      | Milvus元数据         |
| Redis       | 6379      | 缓存服务              |

***

## 常见问题

### Q: 启动后端时报错 "Can't connect to MySQL"

确认 MySQL 服务正在运行，且 `.env` 中的 `DATABASE_URL` 密码正确：

```bash
# 测试MySQL连接
mysql -u root -p -e "SHOW DATABASES;"
```

### Q: Ollama 连接失败

```bash
# 检查 Ollama 是否运行
curl http://localhost:11434/api/tags

# 确认模型已下载
ollama list
```

### Q: Milvus 容器启动后无法连接

等待 60-90 秒，Milvus 首次启动需要较长时间初始化。可通过以下命令检查状态：

```bash
docker logs milvus-standalone | grep "healthy"
```

### Q: 首次对话响应很慢

正常现象。首次对话时：

1. Embedding 模型需要加载到内存（约10-20秒）
2. Rerank 模型需要加载（约5-10秒）
3. LLM 模型需要加载（Ollama首次加载约15-30秒）

后续响应会显著加快。

***

## 许可证

本项目供学术研究和教育用途。

***

**最后更新**：2026年4月21日
