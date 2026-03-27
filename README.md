# CryptoAgent - AI 数字货币交易助手

基于 ReAct 架构的 AI Agent 数字货币交易助手，支持自动化交易决策。

## 功能特性

- 🤖 **AI Agent 交易决策** - 基于 ReAct 架构的智能交易助手
- 📊 **多时间框架分析** - 支持 15m、1H、4H 等多个时间框架
- 📈 **技术指标分析** - 布林带、RSI、MA、MACD、KDJ 等技术指标
- ⏰ **定时任务调度** - 支持多种时间间隔的自动分析
- 📱 **Web 管理界面** - 直观的任务管理和执行历史查看
- 🔑 **多模型支持** - 支持配置多个 AI 模型并切换使用
- 💰 **Token 使用统计** - 详细的 Token 消耗统计
- 🔒 **模拟交易** - 支持模拟盘交易，测试策略零风险

## 架构说明

本项目采用前后端分离架构：

- **API 服务** (端口 8000): 提供 Web API，管理任务、账户、模型配置
- **Agent 服务** (端口 8001): 负责执行交易任务，定时调度
- **前端**: React + TypeScript，提供用户界面

## 快速开始

### 环境要求

- Python 3.13+
- Node.js 18+
- tmux 或 screen（用于后台运行服务）

### 安装步骤

```bash
# 1. 克隆项目
git clone https://github.com/osulivan/CryptoAgent.git
cd CryptoAgent

# 2. 一键安装（会自动创建虚拟环境并安装依赖）
./install.sh
```

### 配置

1. 复制环境变量文件（可选，用于代理等）：
```bash
cp .env.example .env
```

2. 在 Web 界面中配置：
- **交易账户 API 密钥**：进入「账户设置」页面添加
- **AI 模型 API 密钥**：进入「模型设置」页面添加

### 启动服务

```bash
# 开发模式启动（使用 npm run dev）
./start.sh dev

# 生产模式启动（使用构建后的静态文件）
./start.sh prod
```

服务启动后访问：
- 前端: http://localhost:5173
- API: http://localhost:8000
- Agent: http://localhost:8001

### 停止服务

```bash
./stop.sh
```

## 使用指南

### 1. 添加交易账户

进入「账户设置」页：
- 点击「添加账户」
- 填写交易所、API Key、API Secret
- 选择是否模拟交易

### 2. 配置 AI 模型

进入「模型设置」页：
- 点击「添加模型」
- 输入模型名称、Base URL、API Key
- 点击「测试连接」验证
- 设为默认模型

### 3. 创建交易任务

进入「交易任务」页：
- 点击「添加任务」
- 选择交易账户和 AI 模型
- 设置交易品种（如 BTC-USDT-SWAP）
- 编写交易规则（提示词）
- 选择执行间隔
- 保存任务

### 4. 运行任务

- **手动执行**: 点击任务列表中的「执行」按钮
- **定时执行**: 编辑任务，启用「定时执行」

## 项目结构

```
CryptoAgent/
├── src/
│   ├── web/          # API 服务
│   ├── agent/        # AI Agent 核心逻辑
│   ├── agent_service/ # Agent 服务（调度器、执行器）
│   ├── exchange/    # 交易所接口
│   ├── chart/       # K线图生成
│   ├── llm/         # LLM 适配器
│   └── shared/      # 共享代码
├── frontend/         # React 前端
├── data/            # JSON 数据存储
├── start.sh         # 启动脚本
├── stop.sh          # 停止脚本
└── install.sh       # 安装脚本
```

## 技术栈

- **后端**: Python, FastAPI, APScheduler, aiohttp
- **前端**: React, TypeScript, React Query, TailwindCSS
- **AI**: OpenAI Compatible API
- **交易所**: 目前支持Binance, OKX；待支持：Bybit
