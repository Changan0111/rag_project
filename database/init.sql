-- ============================================================
-- 基于RAG的电商场景智能客服机器人 - 数据库初始化脚本
-- 数据库: rag_ecommerce
-- 字符集: utf8mb4
-- ============================================================

CREATE DATABASE IF NOT EXISTS rag_ecommerce
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_0900_ai_ci;

USE rag_ecommerce;

-- ============================================================
-- 用户表
-- ============================================================
CREATE TABLE IF NOT EXISTS `users` (
    `id` int NOT NULL AUTO_INCREMENT COMMENT '主键，自增',
    `username` varchar(50) NOT NULL COMMENT '用户名',
    `password` varchar(255) NOT NULL COMMENT '密码（加密存储）',
    `phone` varchar(20) DEFAULT NULL COMMENT '手机号',
    `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `last_login_at` datetime DEFAULT NULL COMMENT '最后登录时间',
    `role` varchar(20) DEFAULT 'user' COMMENT '角色: admin/user',
    `avatar` varchar(255) DEFAULT '' COMMENT '头像路径',
    PRIMARY KEY (`id`),
    UNIQUE KEY `username` (`username`),
    KEY `idx_users_last_login` (`last_login_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='用户表';

-- ============================================================
-- 商品表
-- ============================================================
CREATE TABLE IF NOT EXISTS `products` (
    `id` int NOT NULL AUTO_INCREMENT COMMENT '主键，自增',
    `name` varchar(200) NOT NULL COMMENT '商品名称',
    `category` varchar(100) DEFAULT NULL COMMENT '商品分类',
    `price` decimal(10,2) NOT NULL COMMENT '商品价格',
    `description` text COMMENT '商品描述',
    `specs` json DEFAULT NULL COMMENT '商品规格（JSON格式）',
    `stock` int DEFAULT '0' COMMENT '库存数量',
    `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    KEY `idx_products_category` (`category`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='商品表';

-- ============================================================
-- 订单表
-- ============================================================
CREATE TABLE IF NOT EXISTS `orders` (
    `id` int NOT NULL AUTO_INCREMENT COMMENT '主键，自增',
    `order_no` varchar(50) NOT NULL COMMENT '订单号',
    `user_id` int NOT NULL COMMENT '用户ID，外键',
    `total_amount` decimal(10,2) NOT NULL COMMENT '订单总金额',
    `status` varchar(20) NOT NULL DEFAULT 'pending' COMMENT '订单状态：pending-待支付, paid-已支付, shipped-已发货, delivered-已送达, cancelled-已取消',
    `payment_method` varchar(50) DEFAULT NULL COMMENT '支付方式',
    `payment_time` datetime DEFAULT NULL COMMENT '支付时间',
    `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `order_no` (`order_no`),
    KEY `idx_orders_user_id` (`user_id`),
    KEY `idx_orders_order_no` (`order_no`),
    KEY `idx_orders_status` (`status`),
    CONSTRAINT `orders_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='订单表';

-- ============================================================
-- 订单详情表
-- ============================================================
CREATE TABLE IF NOT EXISTS `order_items` (
    `id` int NOT NULL AUTO_INCREMENT COMMENT '主键，自增',
    `order_id` int NOT NULL COMMENT '订单ID，外键',
    `product_id` int NOT NULL COMMENT '商品ID，外键',
    `quantity` int NOT NULL DEFAULT '1' COMMENT '购买数量',
    `unit_price` decimal(10,2) NOT NULL COMMENT '单价',
    `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (`id`),
    KEY `idx_order_items_order_id` (`order_id`),
    KEY `idx_order_items_product_id` (`product_id`),
    CONSTRAINT `order_items_ibfk_1` FOREIGN KEY (`order_id`) REFERENCES `orders` (`id`) ON DELETE CASCADE,
    CONSTRAINT `order_items_ibfk_2` FOREIGN KEY (`product_id`) REFERENCES `products` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='订单详情表';

-- ============================================================
-- 物流表
-- ============================================================
CREATE TABLE IF NOT EXISTS `logistics` (
    `id` int NOT NULL AUTO_INCREMENT COMMENT '主键，自增',
    `order_id` int NOT NULL COMMENT '订单ID，外键',
    `tracking_no` varchar(100) DEFAULT NULL COMMENT '快递单号',
    `carrier` varchar(50) DEFAULT NULL COMMENT '快递公司',
    `status` varchar(20) NOT NULL DEFAULT 'pending' COMMENT '物流状态：pending-待发货, shipped-运输中, delivered-已签收',
    `current_location` varchar(200) DEFAULT NULL COMMENT '当前位置',
    `estimated_arrival` date DEFAULT NULL COMMENT '预计到达时间',
    `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    KEY `idx_logistics_order_id` (`order_id`),
    KEY `idx_logistics_tracking_no` (`tracking_no`),
    CONSTRAINT `logistics_ibfk_1` FOREIGN KEY (`order_id`) REFERENCES `orders` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='物流表';

-- ============================================================
-- 物流轨迹表
-- ============================================================
CREATE TABLE IF NOT EXISTS `logistics_tracks` (
    `id` int NOT NULL AUTO_INCREMENT COMMENT '主键，自增',
    `logistics_id` int NOT NULL COMMENT '物流ID，外键',
    `location` varchar(200) DEFAULT NULL COMMENT '所在位置',
    `status` varchar(100) DEFAULT NULL COMMENT '状态描述',
    `track_time` datetime DEFAULT NULL COMMENT '轨迹时间',
    `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (`id`),
    KEY `idx_logistics_tracks_logistics_id` (`logistics_id`),
    CONSTRAINT `logistics_tracks_ibfk_1` FOREIGN KEY (`logistics_id`) REFERENCES `logistics` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='物流轨迹表';

-- ============================================================
-- 对话历史表
-- ============================================================
CREATE TABLE IF NOT EXISTS `chat_history` (
    `id` int NOT NULL AUTO_INCREMENT COMMENT '主键，自增',
    `session_id` varchar(100) NOT NULL COMMENT '会话ID',
    `user_id` int DEFAULT NULL COMMENT '用户ID，外键',
    `role` varchar(20) NOT NULL COMMENT '角色：user-用户, assistant-助手',
    `content` text NOT NULL COMMENT '对话内容',
    `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `source` varchar(20) DEFAULT 'bot' COMMENT '来源: bot-机器人, human-人工',
    `reference_sources` json DEFAULT NULL COMMENT '参考来源列表',
    PRIMARY KEY (`id`),
    KEY `idx_chat_history_session_id` (`session_id`),
    KEY `idx_chat_history_user_id` (`user_id`),
    CONSTRAINT `chat_history_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='对话历史表';

-- ============================================================
-- 人工客服会话表
-- ============================================================
CREATE TABLE IF NOT EXISTS `human_service_sessions` (
    `id` int NOT NULL AUTO_INCREMENT COMMENT '主键，自增',
    `session_id` varchar(100) NOT NULL COMMENT '会话ID',
    `user_id` int NOT NULL COMMENT '用户ID',
    `status` varchar(20) NOT NULL DEFAULT 'pending' COMMENT '状态: pending-等待, active-进行中, closed-已关闭',
    `transfer_reason` varchar(255) DEFAULT NULL COMMENT '转接原因',
    `last_user_message` text COMMENT '最后一条用户消息',
    `assigned_admin_id` int DEFAULT NULL COMMENT '分配的管理员ID',
    `resolved_at` datetime DEFAULT NULL COMMENT '解决时间',
    `last_message_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '最后消息时间',
    `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `ix_human_service_sessions_session_id` (`session_id`),
    KEY `idx_human_service_sessions_status` (`status`),
    KEY `idx_human_service_sessions_user_id` (`user_id`),
    KEY `idx_human_service_sessions_last_message_at` (`last_message_at`),
    KEY `assigned_admin_id` (`assigned_admin_id`),
    CONSTRAINT `human_service_sessions_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`),
    CONSTRAINT `human_service_sessions_ibfk_2` FOREIGN KEY (`assigned_admin_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='人工客服会话表';

-- ============================================================
-- 知识文档表
-- ============================================================
CREATE TABLE IF NOT EXISTS `knowledge_docs` (
    `id` int NOT NULL AUTO_INCREMENT COMMENT '主键，自增',
    `title` varchar(200) NOT NULL COMMENT '文档标题',
    `content` text NOT NULL COMMENT '文档内容',
    `category` varchar(50) NOT NULL COMMENT '分类：product-商品, policy-政策, logistics-物流, service-服务',
    `source` varchar(100) DEFAULT NULL COMMENT '来源',
    `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    KEY `idx_knowledge_docs_category` (`category`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='知识文档表';

-- ============================================================
-- 知识库同步日志表
-- ============================================================
CREATE TABLE IF NOT EXISTS `knowledge_sync_logs` (
    `id` int NOT NULL AUTO_INCREMENT COMMENT '主键，自增',
    `doc_id` int DEFAULT NULL COMMENT '文档ID',
    `action` varchar(20) NOT NULL COMMENT '操作类型: insert/update/delete',
    `status` varchar(20) DEFAULT 'pending' COMMENT '状态: success/failed',
    `error_message` text COMMENT '错误信息',
    `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (`id`),
    KEY `idx_doc_id` (`doc_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='知识库同步日志表';

-- ============================================================
-- 评估记录表
-- ============================================================
CREATE TABLE IF NOT EXISTS `evaluation_records` (
    `id` int NOT NULL AUTO_INCREMENT COMMENT '主键，自增',
    `session_id` varchar(100) DEFAULT NULL COMMENT '会话ID',
    `query` text NOT NULL COMMENT '查询问题',
    `answer` text NOT NULL COMMENT '回答内容',
    `contexts` json DEFAULT NULL COMMENT '上下文内容',
    `ground_truth` text COMMENT '标准答案',
    `faithfulness_score` decimal(3,2) DEFAULT NULL COMMENT '忠实度评分',
    `answer_relevancy_score` decimal(3,2) DEFAULT NULL COMMENT '答案相关性评分',
    `context_precision_score` decimal(3,2) DEFAULT NULL COMMENT '上下文精确度评分',
    `context_recall_score` decimal(3,2) DEFAULT NULL COMMENT '上下文召回率评分',
    `overall_score` decimal(3,2) DEFAULT NULL COMMENT '综合评分',
    `evaluation_framework` varchar(50) DEFAULT 'builtin' COMMENT '评估框架',
    `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (`id`),
    KEY `idx_session_id` (`session_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='评估记录表';

-- ============================================================
-- 评估数据集表
-- ============================================================
CREATE TABLE IF NOT EXISTS `evaluation_dataset` (
    `id` int NOT NULL AUTO_INCREMENT COMMENT '主键，自增',
    `question` text NOT NULL COMMENT '问题',
    `ground_truth` text NOT NULL COMMENT '标准答案',
    `category` varchar(50) DEFAULT NULL COMMENT '分类',
    `relevant_doc_ids` json DEFAULT NULL COMMENT '相关文档ID列表',
    `question_embedding` json DEFAULT NULL COMMENT '问题向量嵌入',
    `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='评估数据集表';
