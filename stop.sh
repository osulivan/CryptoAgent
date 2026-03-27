#!/bin/bash
# CryptoAgent 停止脚本
# 用法: ./stop.sh

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${GREEN}🛑 CryptoAgent 停止脚本${NC}"
echo ""

# 停止 tmux 会话
if command -v tmux &> /dev/null; then
    if tmux has-session -t tradebot 2>/dev/null; then
        echo -e "${YELLOW}正在停止 tmux 会话...${NC}"
        tmux kill-session -t tradebot 2>/dev/null
        echo -e "${GREEN}✓ tmux 会话已停止${NC}"
    else
        echo -e "${BLUE}没有发现 tmux 会话${NC}"
    fi
fi

# 停止 screen 会话
if command -v screen &> /dev/null; then
    for session in tradebot tradebot-api tradebot-agent tradebot-frontend; do
        if screen -ls | grep -q "$session"; then
            echo -e "${YELLOW}正在停止 screen 会话: $session${NC}"
            screen -S "$session" -X quit 2>/dev/null
            echo -e "${GREEN}✓ screen 会话 $session 已停止${NC}"
        fi
    done
fi

# 停止 uvicorn 进程 (API服务)
if pgrep -f "uvicorn.*api:app" > /dev/null; then
    echo -e "${YELLOW}正在停止 API 服务 (uvicorn)...${NC}"
    pkill -f "uvicorn.*api:app"
    echo -e "${GREEN}✓ API 服务已停止${NC}"
fi

# 停止 Agent 服务
if pgrep -f "uvicorn.*main:app.*8001" > /dev/null; then
    echo -e "${YELLOW}正在停止 Agent 服务...${NC}"
    pkill -f "uvicorn.*main:app.*8001"
    echo -e "${GREEN}✓ Agent 服务已停止${NC}"
fi

# 停止 serve 进程 (前端)
if pgrep -f "serve dist" > /dev/null; then
    echo -e "${YELLOW}正在停止前端服务 (serve)...${NC}"
    pkill -f "serve dist"
    echo -e "${GREEN}✓ 前端服务已停止${NC}"
fi

# 停止 node 进程（前端开发服务器）
if pgrep -f "node.*5173" > /dev/null; then
    echo -e "${YELLOW}正在停止前端开发服务器...${NC}"
    pkill -f "node.*5173"
    echo -e "${GREEN}✓ 前端开发服务器已停止${NC}"
fi

echo ""
echo -e "${GREEN}✅ 服务已全部停止${NC}"
