# 移动端AI自动化测试平台设计方案

## 概述

基于自然语言用例执行和智能断言的移动端AI自动化测试平台，支持Android和iOS双平台。

## 设计决策

| 决策项 | 选择 | 说明 |
|--------|------|------|
| 目标平台 | Android + iOS | 跨平台支持 |
| 底层驱动 | 自研方案 | 基于ADB/XCTest封装，灵活可控 |
| AI能力 | 多模型支持 | OpenAI/Claude/通义千问/本地模型可配置切换 |
| 平台形态 | Web平台 | React前端 + FastAPI后端 |
| 设备管理 | 混合模式 | 本地直连 + 远程设备池 |

## 功能优先级

1. 自然语言用例执行
2. 智能断言
3. 用例管理
4. 测试报告

## 一、整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                      Web Frontend                           │
│              (React 18 + TypeScript + Ant Design)           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      API Gateway                            │
│                  (FastAPI + WebSocket)                      │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│  用例管理服务   │   │  执行引擎服务   │   │  设备管理服务   │
│               │   │               │   │               │
│ - 用例CRUD    │   │ - AI解析器    │   │ - 本地设备    │
│ - 版本管理    │   │ - 动作执行器   │   │ - 远程设备池  │
│ - 标签分类    │   │ - 断言引擎    │   │ - 设备调度    │
└───────────────┘   └───────────────┘   └───────────────┘
        │                   │                   │
        └───────────────────┼───────────────────┘
                            ▼
              ┌─────────────────────────┐
              │     驱动适配层           │
              │  ┌─────┐    ┌─────┐     │
              │  │ ADB │    │XCTest│    │
              │  └─────┘    └─────┘     │
              └─────────────────────────┘
```

## 二、核心执行引擎

```
┌─────────────────────────────────────────────────────────────┐
│                    AI Agent 执行引擎                         │
│              (LangChain + LangGraph + FastAPI)              │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│   AI 解析器    │   │   动作执行器   │   │   断言引擎    │
│               │   │               │   │               │
│ - 自然语言理解 │   │ - 三范式降级  │   │ - 视觉断言    │
│ - 步骤分解    │   │ - UI感知导航  │   │ - 数据提取    │
│ - 工具编排    │   │ - 智能重试    │   │ - 结构化输出  │
└───────────────┘   └───────────────┘   └───────────────┘
```

### 三范式自动降级机制

1. **元素交互范式** - 优先通过元素树定位，精确可靠
2. **SoM视觉范式** - 元素定位失败时，使用视觉标注定位
3. **坐标定位范式** - 最后降级到坐标点击，兜底保障

### 智能断言引擎

- **视觉断言**：截图对比、UI元素存在性验证
- **数据断言**：结构化数据提取与验证
- **状态断言**：应用状态、页面状态验证
- **自然语言断言**：用自然语言描述预期结果，AI判断

### 多模型支持架构

```
┌─────────────────────────────────────────┐
│           LLM Provider 抽象层            │
├──────────┬──────────┬──────────┬────────┤
│ OpenAI   │ Claude   │ 通义千问  │ 本地模型 │
│ GPT-4o   │ Sonnet   │ Qwen    │ Ollama  │
└──────────┴──────────┴──────────┴────────┘
```

## 三、Skills 体系设计

```
┌─────────────────────────────────────────────────────────────┐
│                 Layer 1: AI助手技能                          │
│     帮助用户配置平台、创建项目、连接设备                        │
│     示例: platform-setup, create-test-project               │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                 Layer 2: MCP工具集 (核心)                     │
│     39+标准化原子操作，Agent可编排调用                         │
│     示例: tap, swipe, input_text, screenshot, find_element  │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                 Layer 3: 可扩展插件系统                        │
│     用户自定义测试动作，插件化扩展                              │
│     示例: 自定义手势、第三方SDK集成、特殊操作                   │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                 Layer 4: 测试技能库                           │
│     预置的测试场景模板，快速复用                                │
│     示例: login_flow, payment_flow, search_verify           │
└─────────────────────────────────────────────────────────────┘
```

| 层级 | 名称 | 用途 | 示例 |
|------|------|------|------|
| L1 | AI助手技能 | 帮助用户配置平台 | platform-setup, device-connect |
| L2 | MCP工具集 | 原子操作，Agent编排 | tap, swipe, input, screenshot |
| L3 | 插件系统 | 用户自定义扩展 | 自定义手势、SDK集成 |
| L4 | 技能库 | 场景模板复用 | 登录流程、支付流程 |

## 四、设备管理架构

```
┌─────────────────────────────────────────────────────────────┐
│                    设备管理服务                              │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│   本地设备池   │   │   远程设备池   │   │   云测平台    │
│               │   │               │   │               │
│ - USB直连    │   │ - Agent代理   │   │ - Sauce Labs  │
│ - WiFi连接   │   │ - 设备共享    │   │ - BrowserStack│
│ - 模拟器     │   │ - 负载均衡    │   │ - 自定义接入  │
└───────────────┘   └───────────────┘   └───────────────┘
        │                   │                   │
        └───────────────────┼───────────────────┘
                            ▼
              ┌─────────────────────────┐
              │     驱动适配层           │
              │  ┌─────┐    ┌─────┐     │
              │  │ ADB │    │XCTest│    │
              │  │idb  │    │ WDA  │     │
              │  └─────┘    └─────┘     │
              └─────────────────────────┘
```

### 设备连接方式

| 平台 | 本地连接 | 远程连接 | 驱动 |
|------|----------|----------|------|
| Android | ADB USB/WiFi | ADB over TCP | ADB |
| iOS | tidevice + WDA | idb companion | XCTest/WDA |

### 设备调度策略

- **空闲优先**：优先分配空闲设备
- **标签匹配**：根据设备标签（系统版本、分辨率等）智能匹配
- **负载均衡**：远程设备池自动负载均衡
- **独占/共享**：支持设备独占和共享模式

## 五、数据模型与存储

```
┌─────────────────┐     ┌─────────────────┐
│  TestProject    │────<│  TestCase       │
│  - id           │     │  - id           │
│  - name         │     │  - project_id   │
│  - description  │     │  - name         │
│  - created_at   │     │  - steps (JSON) │
└─────────────────┘     │  - assertions   │
                        └─────────────────┘
                               │
                               ▼
┌─────────────────┐     ┌─────────────────┐
│  TestReport     │────<│  TestExecution  │
│  - id           │     │  - id           │
│  - project_id   │     │  - case_id      │
│  - status       │     │  - device_id    │
│  - summary      │     │  - status       │
│  - created_at   │     │  - logs (JSON)  │
└─────────────────┘     │  - screenshots  │
                        └─────────────────┘

┌─────────────────┐     ┌─────────────────┐
│  Device         │     │  LLMConfig      │
│  - id           │     │  - id           │
│  - name         │     │  - provider     │
│  - platform     │     │  - model        │
│  - status       │     │  - api_key      │
│  - capabilities │     │  - base_url     │
└─────────────────┘     └─────────────────┘
```

### 存储策略

- **PostgreSQL**：结构化数据（用例、报告、配置）
- **Redis**：会话缓存、任务队列、实时状态
- **MinIO/OSS**：截图、录屏、日志文件

## 六、前端界面设计

### 美学方向：Neo-Industrial Tech Dashboard

设计理念：融合工业科技感与现代数据可视化，打造专业而独特的测试平台界面。深色基调配合霓虹强调色，几何网格元素贯穿全局。

### 设计特色

| 元素 | 设计选择 | 说明 |
|------|----------|------|
| **配色** | 深空灰 + 霓虹青 | #0D1117 主背景，#00FFD1 强调色 |
| **字体** | JetBrains Mono + Inter Variable | 代码感标题，现代正文 |
| **网格** | 几何线条装饰 | 科技感网格背景 |
| **动效** | 渐入 + 脉冲 | 数据卡片呼吸灯效果 |
| **状态** | 霓虹指示器 | 设备在线/离线霓虹闪烁 |

### 核心页面

| 页面 | 功能 | 关键组件 |
|------|------|----------|
| **仪表盘** | 项目概览、统计数据、最近执行 | 统计卡片、趋势图、快捷入口 |
| **用例管理** | 用例CRUD、步骤编辑、版本管理 | 富文本编辑器、步骤可视化 |
| **执行中心** | 任务创建、实时执行、设备预览 | 设备投屏、日志流、进度条 |
| **设备管理** | 设备列表、状态监控、连接配置 | 设备卡片、状态指示器 |
| **测试报告** | 执行结果、截图日志、统计分析 | 报告详情、截图时间轴、统计图表 |
| **系统设置** | LLM配置、插件管理、系统参数 | 配置表单、插件列表 |

### 实时通信

- WebSocket 实现执行状态推送
- SSE 实现日志流实时输出
- 设备投屏实时画面传输

### 设计系统 Token

```typescript
const designTokens = {
  colors: {
    background: {
      primary: '#0D1117',
      secondary: '#161B22',
      tertiary: '#21262D',
    },
    accent: {
      primary: '#00FFD1',    // 霓虹青
      secondary: '#7B61FF',  // 电子紫
      success: '#3FB950',
      error: '#F85149',
      warning: '#D29922',
    },
    text: {
      primary: '#F0F6FC',
      secondary: '#8B949E',
    }
  },
  fonts: {
    display: 'JetBrains Mono',
    body: 'Inter Variable',
  }
}
```

## 七、API 接口设计

### 核心 API 模块

| 模块 | 端点 | 方法 | 说明 |
|------|------|------|------|
| **用例管理** | `/api/v1/cases` | CRUD | 用例增删改查 |
| **执行任务** | `/api/v1/executions` | POST/GET | 创建/查询执行任务 |
| **设备管理** | `/api/v1/devices` | GET/POST | 设备列表/连接 |
| **测试报告** | `/api/v1/reports` | GET | 报告查询导出 |
| **LLM配置** | `/api/v1/llm-configs` | CRUD | 模型配置管理 |

### 实时通信接口

```
WebSocket 端点:
├── /ws/execution/{id}      # 执行状态实时推送
├── /ws/device/{id}/screen  # 设备画面实时流
└── /ws/logs/{id}           # 日志实时流

SSE 端点:
└── /sse/execution/{id}     # 执行日志流式输出
```

### 核心接口示例

```yaml
# 创建执行任务
POST /api/v1/executions
Request:
  case_id: string
  device_id: string
  llm_config_id: string
Response:
  execution_id: string
  status: "pending"

# 获取设备列表
GET /api/v1/devices
Response:
  devices:
    - id: string
      name: string
      platform: "android" | "ios"
      status: "online" | "offline" | "busy"
      capabilities: object

# 执行结果回调
WebSocket Message:
  type: "step_completed" | "step_failed" | "execution_completed"
  data:
    step: int
    action: string
    result: object
    screenshot: string  # base64
```

## 八、项目目录结构

```
mobiletest/
├── backend/                          # 后端服务
│   ├── app/
│   │   ├── api/                      # API 路由
│   │   │   ├── v1/
│   │   │   │   ├── cases.py
│   │   │   │   ├── executions.py
│   │   │   │   ├── devices.py
│   │   │   │   ├── reports.py
│   │   │   │   └── llm_configs.py
│   │   │   └── websocket.py
│   │   ├── core/                     # 核心模块
│   │   │   ├── config.py
│   │   │   ├── security.py
│   │   │   └── database.py
│   │   ├── models/                   # 数据模型
│   │   │   ├── case.py
│   │   │   ├── execution.py
│   │   │   ├── device.py
│   │   │   └── report.py
│   │   ├── services/                 # 业务服务
│   │   │   ├── case_service.py
│   │   │   ├── execution_service.py
│   │   │   └── device_service.py
│   │   ├── agent/                    # AI Agent 引擎
│   │   │   ├── parser.py             # 自然语言解析
│   │   │   ├── executor.py           # 动作执行器
│   │   │   ├── assertion.py          # 断言引擎
│   │   │   └── llm/                  # LLM 适配层
│   │   │       ├── base.py
│   │   │       ├── openai.py
│   │   │       ├── claude.py
│   │   │       └── qwen.py
│   │   ├── drivers/                  # 设备驱动
│   │   │   ├── base.py
│   │   │   ├── android.py            # ADB 驱动
│   │   │   └── ios.py                # XCTest/WDA 驱动
│   │   ├── mcp/                      # MCP 工具集
│   │   │   ├── server.py
│   │   │   └── tools/
│   │   │       ├── tap.py
│   │   │       ├── swipe.py
│   │   │       ├── input.py
│   │   │       └── ...
│   │   └── main.py
│   ├── tests/
│   ├── requirements.txt
│   └── pyproject.toml
│
├── frontend/                         # 前端应用
│   ├── src/
│   │   ├── components/               # 通用组件
│   │   │   ├── Layout/
│   │   │   ├── DevicePreview/
│   │   │   ├── LogViewer/
│   │   │   └── ...
│   │   ├── pages/                    # 页面
│   │   │   ├── Dashboard/
│   │   │   ├── Cases/
│   │   │   ├── Executions/
│   │   │   ├── Devices/
│   │   │   ├── Reports/
│   │   │   └── Settings/
│   │   ├── hooks/                    # 自定义 Hooks
│   │   ├── stores/                   # Zustand 状态管理
│   │   ├── services/                 # API 服务
│   │   ├── styles/                   # 样式
│   │   └── App.tsx
│   ├── package.json
│   └── vite.config.ts
│
├── skills/                           # AI 助手技能
│   ├── platform-setup/
│   │   └── SKILL.md
│   └── create-project/
│       └── SKILL.md
│
├── plugins/                          # 插件目录
│   └── example-plugin/
│
├── docs/                             # 文档
│   └── plans/
│
├── docker-compose.yml
├── Dockerfile
└── README.md
```

## 参考项目

- [mobile-agent](https://github.com/congwa/mobile-agent.git) - MCP工具 + AI Agent + 可视化操控台
- [mobile-use](https://github.com/minitap-ai/mobile-use.git) - AI agents for Android and iOS apps
