#!/bin/bash
# CryptoAgent 一键安装脚本
# 用法: ./install.sh

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 CryptoAgent 一键安装脚本${NC}"
echo ""

# 检查 Python 版本
echo -e "${YELLOW}📋 检查环境...${NC}"

# 函数：检查 Python 版本是否满足要求
check_python_version() {
    local python_cmd=$1
    local version_output=$($python_cmd --version 2>&1)
    local version=$(echo "$version_output" | awk '{print $2}')
    local major=$(echo "$version" | cut -d. -f1)
    local minor=$(echo "$version" | cut -d. -f2)
    
    if [ "$major" -gt 3 ] || ([ "$major" -eq 3 ] && [ "$minor" -ge 13 ]); then
        echo "$python_cmd"
        return 0
    fi
    return 1
}

# 查找可用的 Python 3.13+
PYTHON_CMD=""

# 尝试不同的 Python 命令
for cmd in python3.13 python3.14 python3 python; do
    if command -v "$cmd" &> /dev/null; then
        if check_python_version "$cmd"; then
            PYTHON_CMD="$cmd"
            PYTHON_VERSION=$($cmd --version 2>&1 | awk '{print $2}')
            break
        fi
    fi
done

# 如果没有找到合适的 Python 版本
if [ -z "$PYTHON_CMD" ]; then
    echo -e "${RED}❌ 错误: 未找到 Python 3.13+${NC}"
    echo ""
    echo -e "${YELLOW}检测到以下 Python 版本:${NC}"
    for cmd in python3 python; do
        if command -v "$cmd" &> /dev/null; then
            echo "  $cmd: $($cmd --version 2>&1)"
        fi
    done
    echo ""
    echo -e "${YELLOW}请安装 Python 3.13 或更高版本:${NC}"
    echo ""
    echo "Ubuntu/Debian:"
    echo "  sudo add-apt-repository ppa:deadsnakes/ppa"
    echo "  sudo apt update"
    echo "  sudo apt install python3.13 python3.13-venv python3.13-pip"
    echo ""
    echo "macOS (使用 Homebrew):"
    echo "  brew install python@3.13"
    echo ""
    echo "或者从源码安装:"
    echo "  https://www.python.org/downloads/"
    echo ""
    exit 1
fi

echo -e "${GREEN}✓ Python 版本: $PYTHON_VERSION${NC}"

# 检查 Node.js
if ! command -v node &> /dev/null; then
    echo -e "${RED}❌ 错误: 未找到 Node.js，请先安装 Node.js 18+${NC}"
    echo "安装指南: https://nodejs.org/"
    exit 1
fi

NODE_VERSION=$(node --version)
echo -e "${GREEN}✓ Node.js 版本: $NODE_VERSION${NC}"

# 检查 npm
if ! command -v npm &> /dev/null; then
    echo -e "${RED}❌ 错误: 未找到 npm${NC}"
    exit 1
fi
echo -e "${GREEN}✓ npm 已安装${NC}"
echo ""

# 检查并安装 tmux（用于后台运行服务）
echo -e "${YELLOW}📦 检查 tmux（用于后台运行）...${NC}"
if ! command -v tmux &> /dev/null; then
    echo -e "${YELLOW}⚠️  未找到 tmux，正在自动安装...${NC}"

    # 检测系统并安装
    if command -v apt-get &> /dev/null; then
        # Debian/Ubuntu
        sudo apt-get update -qq && sudo apt-get install -y tmux
    elif command -v yum &> /dev/null; then
        # CentOS/RHEL
        sudo yum install -y tmux
    elif command -v dnf &> /dev/null; then
        # Fedora
        sudo dnf install -y tmux
    elif command -v apk &> /dev/null; then
        # Alpine
        sudo apk add tmux
    else
        echo -e "${YELLOW}⚠️  无法自动安装 tmux，请手动安装: sudo apt install tmux${NC}"
    fi

    # 验证安装
    if command -v tmux &> /dev/null; then
        echo -e "${GREEN}✓ tmux 安装完成${NC}"
    else
        echo -e "${YELLOW}⚠️  tmux 安装失败，启动时将使用前台模式${NC}"
    fi
else
    echo -e "${GREEN}✓ tmux 已安装${NC}"
fi
echo ""

# 创建虚拟环境
echo -e "${YELLOW}📦 创建 Python 虚拟环境...${NC}"
if [ ! -d "venv" ]; then
    $PYTHON_CMD -m venv venv
    echo -e "${GREEN}✓ 虚拟环境创建完成${NC}"
else
    echo -e "${GREEN}✓ 虚拟环境已存在${NC}"
fi

# 激活虚拟环境
echo -e "${YELLOW}📦 安装 Python 依赖...${NC}"
source venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
echo -e "${GREEN}✓ Python 依赖安装完成${NC}"
echo ""

# 安装前端依赖
echo -e "${YELLOW}📦 安装前端依赖...${NC}"
cd frontend
npm install
echo -e "${GREEN}✓ 前端依赖安装完成${NC}"
echo ""

# 构建前端
echo -e "${YELLOW}🔨 构建前端...${NC}"
npm run build
echo -e "${GREEN}✓ 前端构建完成${NC}"
cd ..
echo ""

# 检查环境变量文件
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  未找到 .env 文件，从示例创建...${NC}"
    cp .env.example .env
    echo -e "${YELLOW}⚠️  请编辑 .env 文件，配置 OKX API 密钥${NC}"
fi

echo ""
echo -e "${GREEN}🎉 安装完成！${NC}"
echo ""
echo -e "${BLUE}启动应用:${NC}"
echo "  ./start.sh"
echo ""
echo -e "${BLUE}或者分别启动:${NC}"
echo "  终端1: ./run_server.sh"
echo "  终端2: ./run_agent.sh"
echo "  终端3: cd frontend && npm run preview"
echo ""
