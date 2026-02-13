# MobileTest AI - 本地运行指南

## 环境要求

- Python 3.11+
- Node.js 18+
- PostgreSQL (可选，默认使用 SQLite)
- Redis (可选)
- ADB (Android Debug Bridge)
- scrcpy (屏幕投影，可选)

## 快速开始

### 1. 后端启动

```bash
# 进入后端目录
cd backend

# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 配置环境变量 (可选)
cp .env.example .env
# 编辑 .env 文件配置 API Keys

# 启动后端服务
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. 前端启动

```bash
# 新开终端，进入前端目录
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

### 3. 访问应用

- 前端: http://localhost:5173
- 后端 API: http://localhost:8000
- API 文档: http://localhost:8000/docs

## 环境变量配置

创建 `backend/.env` 文件：

```bash
# 应用配置
DEBUG=true
APP_NAME=MobileTest AI

# 数据库 (默认 SQLite)
DATABASE_URL=sqlite+aiosqlite:///./mobiletest.db

# PostgreSQL (可选)
# DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/mobile_test

# Redis (可选)
REDIS_URL=redis://localhost:6379/0

# LLM 配置
OPENAI_API_KEY=your-openai-api-key
OPENAI_BASE_URL=https://api.openai.com/v1
ANTHROPIC_API_KEY=your-anthropic-api-key
DASHSCOPE_API_KEY=your-dashscope-api-key

# LangGraph 配置
LANGGRAPH_PLANNER_MODE=stub
LANGGRAPH_SYNTHESIZE_MODE=stub
LANGGRAPH_EXECUTE_LIVE_TOOLS=false
LANGGRAPH_CHECKPOINTER_BACKEND=sqlite

# CORS
CORS_ALLOW_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

## 设备连接

### Android 设备

```bash
# USB 连接
adb devices

# 无线连接 (Android 11+)
adb tcpip 5555
adb connect <设备IP>:5555
```

### iOS 模拟器 (macOS)

```bash
# 安装 idb
brew tap facebook/fb
brew install idb-companion

# 启动模拟器
xcrun simctl boot "iPhone 15"
```

## 常用命令

```bash
# 后端测试
cd backend
pytest

# 前端构建
cd frontend
npm run build

# 代码检查
cd backend
ruff check app/
mypy app/
```

## 项目结构

```
mobiletest/
├── backend/
│   ├── app/
│   │   ├── api/v1/        # API 路由
│   │   ├── core/          # 核心配置
│   │   ├── models/        # 数据库模型
│   │   ├── services/      # 业务服务
│   │   ├── orchestrator/  # LangGraph 编排
│   │   ├── agent/         # Agent 核心
│   │   └── drivers/       # 设备驱动
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   ├── package.json
│   └── vite.config.ts
└── docker-compose.yml
```
