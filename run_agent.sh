#!/bin/bash
# 启动 Agent 服务脚本
# 用法: ./run_agent.sh

cd "$(dirname "$0")"

# 激活虚拟环境
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# 加载环境变量
if [ -f ".env" ]; then
    echo "🚀 加载环境变量 (.env)"
    export $(grep -v '^#' .env | xargs)
else
    echo "⚠️  未找到 .env 文件，使用系统环境变量"
fi

# 显示配置信息
echo ""
echo "📊 Agent 服务配置:"
echo "  端口: 8001"
echo "  API服务地址: http://localhost:8000"
echo ""

# 启动 Agent 服务
echo "🤖 启动 Agent 服务..."
python3 -m uvicorn src.agent_service.main:app --reload --host 0.0.0.0 --port 8001
