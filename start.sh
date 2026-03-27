#!/bin/bash
# CryptoAgent 一键启动脚本
# 用法: ./start.sh

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${GREEN}🚀 CryptoAgent 启动脚本${NC}"
echo ""

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo -e "${RED}❌ 错误: 未找到虚拟环境，请先运行 ./install.sh${NC}"
    exit 1
fi

# 检查环境变量
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ 错误: 未找到 .env 文件${NC}"
    echo "请复制 .env.example 为 .env 并配置 OKX API 密钥"
    exit 1
fi

# 检查前端构建
if [ ! -d "frontend/dist" ]; then
    echo -e "${YELLOW}⚠️  前端未构建，正在构建...${NC}"
    cd frontend
    npm install
    npm run build
    cd ..
fi

echo -e "${YELLOW}📝 启动模式选择:${NC}"
echo "  1) 开发模式 (前后端分离，热重载)"
echo "  2) 生产模式 (前端使用预览服务器)"
echo ""
read -p "请选择 [1/2，默认2]: " mode
mode=${mode:-2}

echo ""

if [ "$mode" = "1" ]; then
    # 开发模式
    echo -e "${GREEN}🚀 启动开发模式...${NC}"
    echo ""

    # 检查 tmux 或 screen
    if command -v tmux &> /dev/null; then
        echo -e "${YELLOW}使用 tmux 启动服务...${NC}"

        # 创建 tmux 会话
        tmux new-session -d -s tradebot -n api
        tmux send-keys -t tradebot:api "source venv/bin/activate && ./run_server.sh" C-m

        tmux new-window -t tradebot -n agent
        tmux send-keys -t tradebot:agent "source venv/bin/activate && ./run_agent.sh" C-m

        tmux new-window -t tradebot -n frontend
        tmux send-keys -t tradebot:frontend "cd frontend && npm run dev" C-m

        echo -e "${GREEN}✅ 服务已启动！${NC}"
        echo ""
        echo -e "${BLUE}访问地址:${NC}"
        echo "  前端: http://localhost:5173"
        echo "  API:  http://localhost:8000"
        echo "  Agent: http://localhost:8001"
        echo ""
        echo -e "${BLUE}tmux 管理命令:${NC}"
        echo "  查看会话: tmux attach -t tradebot"
        echo "  切换窗口: Ctrl+B, 然后按数字 0/1/2"
        echo "  分离会话: Ctrl+B, 然后按 D"
        echo "  停止服务: tmux kill-session -t tradebot"
        echo ""

    elif command -v screen &> /dev/null; then
        echo -e "${YELLOW}使用 screen 启动服务...${NC}"

        # 创建 screen 会话
        screen -dmS tradebot-api bash -c "source venv/bin/activate && ./run_server.sh"
        screen -dmS tradebot-agent bash -c "source venv/bin/activate && ./run_agent.sh"
        screen -dmS tradebot-frontend bash -c "cd frontend && npm run dev"

        echo -e "${GREEN}✅ 服务已启动！${NC}"
        echo ""
        echo -e "${BLUE}访问地址:${NC}"
        echo "  前端: http://localhost:5173"
        echo "  API:  http://localhost:8000"
        echo "  Agent: http://localhost:8001"
        echo ""
        echo -e "${BLUE}screen 管理命令:${NC}"
        echo "  查看API: screen -r tradebot-api"
        echo "  查看Agent: screen -r tradebot-agent"
        echo "  查看前端: screen -r tradebot-frontend"
        echo "  分离: Ctrl+A, 然后按 D"
        echo "  停止: screen -S tradebot-api -X quit; screen -S tradebot-agent -X quit; screen -S tradebot-frontend -X quit"
        echo ""

    else
        echo -e "${YELLOW}未找到 tmux 或 screen，将在前台启动...${NC}"
        echo -e "${YELLOW}请打开三个终端分别运行:${NC}"
        echo "  终端1: ./run_server.sh"
        echo "  终端2: ./run_agent.sh"
        echo "  终端3: cd frontend && npm run dev"
        echo ""
    fi

else
    # 生产模式
    echo -e "${GREEN}🚀 启动生产模式...${NC}"
    echo ""

    # 检查 tmux 或 screen
    if command -v tmux &> /dev/null; then
        echo -e "${YELLOW}使用 tmux 启动服务...${NC}"

        # 停止已存在的会话
        tmux kill-session -t tradebot 2>/dev/null || true

        # 创建 tmux 会话
        tmux new-session -d -s tradebot -n api
        tmux send-keys -t tradebot:api "source venv/bin/activate && ./run_server.sh" C-m

        tmux new-window -t tradebot -n agent
        tmux send-keys -t tradebot:agent "source venv/bin/activate && ./run_agent.sh" C-m

        tmux new-window -t tradebot -n frontend
        tmux send-keys -t tradebot:frontend "cd frontend && npx --yes serve -s dist -l tcp://0.0.0.0:5173" C-m

        echo -e "${GREEN}✅ 服务已启动！${NC}"
        echo ""
        echo -e "${BLUE}访问地址:${NC}"
        echo "  应用:  http://localhost:5173"
        echo "  API:   http://localhost:8000"
        echo "  Agent: http://localhost:8001"
        echo ""
        echo -e "${BLUE}tmux 管理命令:${NC}"
        echo "  查看会话: tmux attach -t tradebot"
        echo "  切换窗口: Ctrl+B, 然后按数字 0/1/2"
        echo "  分离会话: Ctrl+B, 然后按 D"
        echo "  停止服务: tmux kill-session -t tradebot"
        echo ""

    elif command -v screen &> /dev/null; then
        echo -e "${YELLOW}使用 screen 启动服务...${NC}"

        # 停止已存在的会话
        screen -S tradebot-api -X quit 2>/dev/null || true
        screen -S tradebot-agent -X quit 2>/dev/null || true
        screen -S tradebot-frontend -X quit 2>/dev/null || true

        # 创建 screen 会话
        screen -dmS tradebot-api bash -c "source venv/bin/activate && ./run_server.sh"
        screen -dmS tradebot-agent bash -c "source venv/bin/activate && ./run_agent.sh"
        screen -dmS tradebot-frontend bash -c "cd frontend && npx --yes serve -s dist -l tcp://0.0.0.0:5173"

        echo -e "${GREEN}✅ 服务已启动！${NC}"
        echo ""
        echo -e "${BLUE}访问地址:${NC}"
        echo "  应用:  http://localhost:5173"
        echo "  API:   http://localhost:8000"
        echo "  Agent: http://localhost:8001"
        echo ""
        echo -e "${BLUE}screen 管理命令:${NC}"
        echo "  查看API: screen -r tradebot-api"
        echo "  查看Agent: screen -r tradebot-agent"
        echo "  查看前端: screen -r tradebot-frontend"
        echo "  分离: Ctrl+A, 然后按 D"
        echo "  停止: screen -S tradebot-api -X quit; screen -S tradebot-agent -X quit; screen -S tradebot-frontend -X quit"
        echo ""

    else
        echo -e "${YELLOW}未找到 tmux 或 screen，将在前台启动...${NC}"
        echo ""

        echo -e "${BLUE}启动API服务...${NC}"
        source venv/bin/activate && ./run_server.sh &
        API_PID=$!

        echo -e "${BLUE}启动Agent服务...${NC}"
        source venv/bin/activate && ./run_agent.sh &
        AGENT_PID=$!

        echo -e "${BLUE}启动前端服务...${NC}"
        cd frontend && npx --yes serve -s dist -l tcp://0.0.0.0:5173 &
        FRONTEND_PID=$!

        echo ""
        echo -e "${GREEN}✅ 服务已启动！${NC}"
        echo ""
        echo -e "${BLUE}访问地址:${NC}"
        echo "  应用:  http://localhost:5173"
        echo "  API:   http://localhost:8000"
        echo "  Agent: http://localhost:8001"
        echo ""
        echo -e "${YELLOW}按 Ctrl+C 停止服务${NC}"

        # 等待中断信号
        trap "kill $API_PID $AGENT_PID $FRONTEND_PID 2>/dev/null; exit" INT
        wait
    fi
fi
