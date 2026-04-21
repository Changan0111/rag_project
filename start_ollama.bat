@echo off
chcp 65001 >nul
echo ==============================================
echo    Ollama RTX 3050 4GB 【qwen2.5:3b 专用优化版】
echo ==============================================

:: 显卡指定
set CUDA_VISIBLE_DEVICES=0

:: GPU 加速（3B + 4G 显存最稳的层数）
set OLLAMA_GPU_LAYERS=35
set OLLAMA_NUM_GPU=35

:: 并行与并发（RAGAS 评估专用，不炸显存）
set OLLAMA_NUM_PARALEL=2
set OLLAMA_MAX_LOADED_MODELS=1

:: 上下文 & 性能
set OLLAMA_CONTEXT_LENGTH=4096
set OLLAMA_KEEP_ALIVE=1h
set OLLAMA_FLASH_ATTENTION=false

echo 环境加载完成 ✅
echo GPU: RTX 3050 4GB
echo 模型: qwen2.5:3b
echo 加速: 部分GPU推理 + 稳定不爆显存
echo 并发: 支持 RAGAS 并行评估
echo.

echo 关闭旧进程...
taskkill /f /im ollama.exe >nul 2>&1
timeout /t 1 /nobreak >nul

echo.
echo 启动 Ollama 服务...
ollama serve

pause