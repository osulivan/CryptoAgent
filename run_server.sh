#!/bin/bash
# 启动后端服务脚本
# 用法: ./run_server.sh

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
echo "📊 当前配置:"
echo "  代理: ${HTTP_PROXY:-未设置}"
echo "  模拟交易: ${SIMULATED_TRADING:-未设置}"
echo ""

# 启动服务
echo "🌐 启动后端服务..."
python3 -m uvicorn src.web.api:app --reload --host 0.0.0.0 --port 8000
