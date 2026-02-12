# 移动端AI自动化测试平台实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 构建一个支持自然语言用例执行和智能断言的移动端AI自动化测试平台，支持Android和iOS双平台。

**Architecture:** 采用前后端分离架构，后端使用FastAPI + LangChain构建AI Agent执行引擎，前端使用React构建Web管理界面。通过自研驱动层抽象ADB/XCTest差异，实现跨平台设备控制。

**Tech Stack:** Python 3.11+ / FastAPI / LangChain / LangGraph / React 18 / TypeScript / PostgreSQL / Redis / ADB / XCTest

---

## Phase 1: 项目骨架搭建

### Task 1.1: 初始化后端项目结构

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/requirements.txt`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/core/__init__.py`
- Create: `backend/app/core/config.py`

**Step 1: 创建项目目录结构**

```bash
mkdir -p backend/app/{api/v1,core,models,services,agent/llm,drivers,mcp/tools}
mkdir -p backend/tests
touch backend/app/__init__.py
touch backend/app/api/__init__.py
touch backend/app/api/v1/__init__.py
touch backend/app/core/__init__.py
touch backend/app/models/__init__.py
touch backend/app/services/__init__.py
touch backend/app/agent/__init__.py
touch backend/app/agent/llm/__init__.py
touch backend/app/drivers/__init__.py
touch backend/app/mcp/__init__.py
touch backend/app/mcp/tools/__init__.py
touch backend/tests/__init__.py
```

**Step 2: 创建 pyproject.toml**

```toml
[project]
name = "mobile-test-ai"
version = "0.1.0"
description = "Mobile AI Automation Testing Platform"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.109.0",
    "uvicorn[standard]>=0.27.0",
    "pydantic>=2.5.0",
    "pydantic-settings>=2.1.0",
    "sqlalchemy>=2.0.0",
    "asyncpg>=0.29.0",
    "redis>=5.0.0",
    "langchain>=0.1.0",
    "langchain-openai>=0.0.5",
    "langchain-anthropic>=0.1.0",
    "langgraph>=0.0.40",
    "httpx>=0.26.0",
    "websockets>=12.0",
    "python-multipart>=0.0.6",
    "python-jose[cryptography]>=3.3.0",
    "passlib[bcrypt]>=1.7.4",
    "pure-python-adb>=0.3.0.dev0",
    "pillow>=10.0.0",
    "mss>=9.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=4.1.0",
    "httpx>=0.26.0",
    "ruff>=0.1.0",
    "mypy>=1.8.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.mypy]
python_version = "3.11"
strict = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

**Step 3: 创建 core/config.py**

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Mobile Test AI"
    debug: bool = False
    
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/mobile_test"
    redis_url: str = "redis://localhost:6379/0"
    
    jwt_secret: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    
    class Config:
        env_file = ".env"


settings = Settings()
```

**Step 4: 创建 main.py**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings

app = FastAPI(
    title=settings.app_name,
    description="Mobile AI Automation Testing Platform",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    return {"status": "ok", "app": settings.app_name}
```

**Step 5: 验证后端启动**

```bash
cd backend
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8088
```

访问 http://localhost:8088/health 应返回 `{"status": "ok", "app": "Mobile Test AI"}`

**Step 6: Commit**

```bash
git add backend/
git commit -m "feat(backend): initialize project structure with FastAPI"
```

---

### Task 1.2: 初始化前端项目结构

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`

**Step 1: 使用 Vite 创建 React 项目**

```bash
cd /Users/lisq/ai/mobileagent/mobiletest
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
```

**Step 2: 安装依赖**

```bash
npm install antd @ant-design/icons zustand @tanstack/react-query axios react-router-dom
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

**Step 3: 配置 tailwind.config.js**

```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: {
          primary: '#0D1117',
          secondary: '#161B22',
          tertiary: '#21262D',
        },
        accent: {
          primary: '#00FFD1',
          secondary: '#7B61FF',
          success: '#3FB950',
          error: '#F85149',
          warning: '#D29922',
        },
        text: {
          primary: '#F0F6FC',
          secondary: '#8B949E',
        }
      },
      fontFamily: {
        display: ['JetBrains Mono', 'monospace'],
        body: ['Inter Variable', 'sans-serif'],
      }
    },
  },
  plugins: [],
}
```

**Step 4: 创建 src/styles/globals.css**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

body {
  @apply bg-background-primary text-text-primary font-body;
}
```

**Step 5: 验证前端启动**

```bash
npm run dev
```

访问 http://localhost:5173 应看到 Vite + React 页面

**Step 6: Commit**

```bash
git add frontend/
git commit -m "feat(frontend): initialize React project with Vite and Tailwind"
```

---

## Phase 2: 核心数据模型

### Task 2.1: 实现数据库模型

**Files:**
- Create: `backend/app/core/database.py`
- Create: `backend/app/models/base.py`
- Create: `backend/app/models/case.py`
- Create: `backend/app/models/device.py`
- Create: `backend/app/models/execution.py`
- Create: `backend/app/models/report.py`
- Create: `backend/app/models/llm_config.py`

**Step 1: 创建 database.py**

```python
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

engine = create_async_engine(settings.database_url, echo=settings.debug)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

**Step 2: 创建 models/base.py**

```python
from datetime import datetime
from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
```

**Step 3: 创建 models/case.py**

```python
from typing import Optional
from sqlalchemy import String, Text, JSON, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TimestampMixin
from app.core.database import Base


class TestProject(Base, TimestampMixin):
    __tablename__ = "test_projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    cases: Mapped[list["TestCase"]] = relationship("TestCase", back_populates="project")


class TestCase(Base, TimestampMixin):
    __tablename__ = "test_cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("test_projects.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    steps: Mapped[list] = mapped_column(JSON, default=list)
    assertions: Mapped[list] = mapped_column(JSON, default=list)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    
    project: Mapped["TestProject"] = relationship("TestProject", back_populates="cases")
```

**Step 4: 创建 models/device.py**

```python
from typing import Optional
from sqlalchemy import String, JSON, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column
import enum

from app.models.base import TimestampMixin
from app.core.database import Base


class DevicePlatform(str, enum.Enum):
    ANDROID = "android"
    IOS = "ios"


class DeviceStatus(str, enum.Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    BUSY = "busy"


class Device(Base, TimestampMixin):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    platform: Mapped[DevicePlatform] = mapped_column(SQLEnum(DevicePlatform), nullable=False)
    status: Mapped[DeviceStatus] = mapped_column(SQLEnum(DeviceStatus), default=DeviceStatus.OFFLINE)
    serial: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    capabilities: Mapped[dict] = mapped_column(JSON, default=dict)
```

**Step 5: 创建 models/execution.py**

```python
from typing import Optional
from sqlalchemy import String, Text, JSON, ForeignKey, Integer, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.models.base import TimestampMixin
from app.core.database import Base


class ExecutionStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


class TestExecution(Base, TimestampMixin):
    __tablename__ = "test_executions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("test_cases.id"), nullable=False)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), nullable=False)
    llm_config_id: Mapped[int] = mapped_column(ForeignKey("llm_configs.id"), nullable=False)
    status: Mapped[ExecutionStatus] = mapped_column(SQLEnum(ExecutionStatus), default=ExecutionStatus.PENDING)
    logs: Mapped[list] = mapped_column(JSON, default=list)
    screenshots: Mapped[list] = mapped_column(JSON, default=list)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    case: Mapped["TestCase"] = relationship("TestCase")
    device: Mapped["Device"] = relationship("Device")
```

**Step 6: 创建 models/llm_config.py**

```python
from typing import Optional
from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TimestampMixin
from app.core.database import Base


class LLMConfig(Base, TimestampMixin):
    __tablename__ = "llm_configs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    api_key: Mapped[str] = mapped_column(String(255), nullable=False)
    base_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
```

**Step 7: 编写测试**

```python
# backend/tests/test_models.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.case import TestProject, TestCase
from app.models.device import Device, DevicePlatform, DeviceStatus
from app.models.llm_config import LLMConfig


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_create_project(db_session):
    project = TestProject(name="Test Project", description="A test project")
    db_session.add(project)
    db_session.commit()
    
    assert project.id is not None
    assert project.name == "Test Project"


def test_create_device(db_session):
    device = Device(
        name="Test Device",
        platform=DevicePlatform.ANDROID,
        status=DeviceStatus.ONLINE,
        serial="emulator-5554"
    )
    db_session.add(device)
    db_session.commit()
    
    assert device.id is not None
    assert device.platform == DevicePlatform.ANDROID


def test_create_llm_config(db_session):
    config = LLMConfig(
        name="GPT-4o",
        provider="openai",
        model="gpt-4o",
        api_key="sk-test",
        is_default=True
    )
    db_session.add(config)
    db_session.commit()
    
    assert config.id is not None
    assert config.provider == "openai"
```

**Step 8: 运行测试**

```bash
cd backend
pytest tests/test_models.py -v
```

**Step 9: Commit**

```bash
git add backend/app/core/database.py backend/app/models/ backend/tests/test_models.py
git commit -m "feat(backend): add database models for cases, devices, executions, and llm configs"
```

---

## Phase 3: 设备驱动层

### Task 3.1: 实现驱动基类

**Files:**
- Create: `backend/app/drivers/base.py`
- Create: `backend/tests/test_drivers.py`

**Step 1: 创建 base.py**

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional
from PIL import Image


class ElementType(Enum):
    BUTTON = "button"
    TEXT = "text"
    INPUT = "input"
    IMAGE = "image"
    CONTAINER = "container"
    UNKNOWN = "unknown"


@dataclass
class Element:
    id: Optional[str]
    text: Optional[str]
    bounds: tuple[int, int, int, int]  # x, y, width, height
    element_type: ElementType
    attributes: dict


@dataclass
class DeviceInfo:
    name: str
    platform: str
    version: str
    resolution: tuple[int, int]
    serial: str


class BaseDriver(ABC):
    def __init__(self, serial: str):
        self.serial = serial
        self._connected = False

    @abstractmethod
    async def connect(self) -> bool:
        """连接设备"""
        pass

    @abstractmethod
    async def disconnect(self) -> bool:
        """断开连接"""
        pass

    @abstractmethod
    async def get_device_info(self) -> DeviceInfo:
        """获取设备信息"""
        pass

    @abstractmethod
    async def screenshot(self) -> Image.Image:
        """截取屏幕"""
        pass

    @abstractmethod
    async def tap(self, x: int, y: int) -> bool:
        """点击坐标"""
        pass

    @abstractmethod
    async def swipe(self, start_x: int, start_y: int, end_x: int, end_y: int, duration: float = 0.3) -> bool:
        """滑动"""
        pass

    @abstractmethod
    async def input_text(self, text: str) -> bool:
        """输入文本"""
        pass

    @abstractmethod
    async def press_key(self, key: str) -> bool:
        """按键"""
        pass

    @abstractmethod
    async def get_elements(self) -> list[Element]:
        """获取元素树"""
        pass

    @abstractmethod
    async def find_element(self, text: str = None, id: str = None) -> Optional[Element]:
        """查找元素"""
        pass

    @property
    def is_connected(self) -> bool:
        return self._connected
```

**Step 2: 编写测试**

```python
# backend/tests/test_drivers.py
import pytest
from app.drivers.base import BaseDriver, Element, ElementType, DeviceInfo


class MockDriver(BaseDriver):
    async def connect(self) -> bool:
        self._connected = True
        return True

    async def disconnect(self) -> bool:
        self._connected = False
        return True

    async def get_device_info(self) -> DeviceInfo:
        return DeviceInfo(
            name="Mock Device",
            platform="mock",
            version="1.0",
            resolution=(1080, 1920),
            serial=self.serial
        )

    async def screenshot(self):
        from PIL import Image
        return Image.new('RGB', (1080, 1920), color='white')

    async def tap(self, x: int, y: int) -> bool:
        return True

    async def swipe(self, start_x: int, start_y: int, end_x: int, end_y: int, duration: float = 0.3) -> bool:
        return True

    async def input_text(self, text: str) -> bool:
        return True

    async def press_key(self, key: str) -> bool:
        return True

    async def get_elements(self) -> list[Element]:
        return []

    async def find_element(self, text: str = None, id: str = None):
        return None


@pytest.mark.asyncio
async def test_mock_driver_connect():
    driver = MockDriver("test-serial")
    assert not driver.is_connected
    
    result = await driver.connect()
    assert result is True
    assert driver.is_connected


@pytest.mark.asyncio
async def test_mock_driver_device_info():
    driver = MockDriver("test-serial")
    await driver.connect()
    
    info = await driver.get_device_info()
    assert info.name == "Mock Device"
    assert info.serial == "test-serial"
```

**Step 3: 运行测试**

```bash
cd backend
pytest tests/test_drivers.py -v
```

**Step 4: Commit**

```bash
git add backend/app/drivers/base.py backend/tests/test_drivers.py
git commit -m "feat(backend): add base driver abstraction for device control"
```

---

### Task 3.2: 实现 Android ADB 驱动

**Files:**
- Create: `backend/app/drivers/android.py`
- Create: `backend/tests/test_android_driver.py`

**Step 1: 创建 android.py**

```python
import asyncio
import re
from io import BytesIO
from typing import Optional
from PIL import Image

from app.drivers.base import BaseDriver, Element, ElementType, DeviceInfo


class AndroidDriver(BaseDriver):
    def __init__(self, serial: str):
        super().__init__(serial)
        self._adb_path = "adb"

    async def _run_adb(self, *args) -> tuple[int, str, str]:
        """执行 ADB 命令"""
        cmd = [self._adb_path, "-s", self.serial] + list(args)
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        return proc.returncode, stdout.decode(), stderr.decode()

    async def connect(self) -> bool:
        """连接设备"""
        returncode, _, _ = await self._run_adb("devices")
        if returncode == 0:
            self._connected = True
            return True
        return False

    async def disconnect(self) -> bool:
        """断开连接"""
        self._connected = False
        return True

    async def get_device_info(self) -> DeviceInfo:
        """获取设备信息"""
        _, name, _ = await self._run_adb("shell", "getprop", "ro.product.model")
        _, version, _ = await self._run_adb("shell", "getprop", "ro.build.version.release")
        _, size, _ = await self._run_adb("shell", "wm", "size")
        
        resolution = (1080, 1920)
        if "Physical size:" in size:
            match = re.search(r"(\d+)x(\d+)", size)
            if match:
                resolution = (int(match.group(1)), int(match.group(2)))

        return DeviceInfo(
            name=name.strip() or "Unknown",
            platform="android",
            version=version.strip() or "Unknown",
            resolution=resolution,
            serial=self.serial
        )

    async def screenshot(self) -> Image.Image:
        """截取屏幕"""
        returncode, stdout, _ = await self._run_adb("exec-out", "screencap", "-p")
        if returncode == 0:
            return Image.open(BytesIO(stdout.encode('latin1')))
        raise RuntimeError("Failed to take screenshot")

    async def tap(self, x: int, y: int) -> bool:
        """点击坐标"""
        returncode, _, _ = await self._run_adb("shell", "input", "tap", str(x), str(y))
        return returncode == 0

    async def swipe(self, start_x: int, start_y: int, end_x: int, end_y: int, duration: float = 0.3) -> bool:
        """滑动"""
        duration_ms = int(duration * 1000)
        returncode, _, _ = await self._run_adb(
            "shell", "input", "swipe",
            str(start_x), str(start_y), str(end_x), str(end_y), str(duration_ms)
        )
        return returncode == 0

    async def input_text(self, text: str) -> bool:
        """输入文本"""
        escaped = text.replace(" ", "%s").replace("'", "\\'")
        returncode, _, _ = await self._run_adb("shell", "input", "text", escaped)
        return returncode == 0

    async def press_key(self, key: str) -> bool:
        """按键"""
        key_map = {
            "back": "KEYCODE_BACK",
            "home": "KEYCODE_HOME",
            "enter": "KEYCODE_ENTER",
            "delete": "KEYCODE_DEL",
        }
        keycode = key_map.get(key.lower(), key)
        returncode, _, _ = await self._run_adb("shell", "input", "keyevent", keycode)
        return returncode == 0

    async def get_elements(self) -> list[Element]:
        """获取元素树 (使用 uiautomator dump)"""
        await self._run_adb("shell", "uiautomator", "dump", "/sdcard/ui.xml")
        returncode, stdout, _ = await self._run_adb("shell", "cat", "/sdcard/ui.xml")
        
        if returncode != 0:
            return []
        
        return self._parse_ui_dump(stdout)

    def _parse_ui_dump(self, xml_content: str) -> list[Element]:
        """解析 UI dump XML"""
        import xml.etree.ElementTree as ET
        elements = []
        
        try:
            root = ET.fromstring(xml_content)
            for node in root.iter():
                bounds_str = node.attrib.get("bounds", "[0,0][0,0]")
                match = re.findall(r"\[(\d+),(\d+)\]", bounds_str)
                if len(match) == 2:
                    bounds = (int(match[0][0]), int(match[0][1]), 
                              int(match[1][0]) - int(match[0][0]),
                              int(match[1][1]) - int(match[0][1]))
                else:
                    bounds = (0, 0, 0, 0)
                
                element = Element(
                    id=node.attrib.get("resource-id"),
                    text=node.attrib.get("text"),
                    bounds=bounds,
                    element_type=ElementType.UNKNOWN,
                    attributes=node.attrib
                )
                elements.append(element)
        except ET.ParseError:
            pass
        
        return elements

    async def find_element(self, text: str = None, id: str = None) -> Optional[Element]:
        """查找元素"""
        elements = await self.get_elements()
        for element in elements:
            if text and element.text and text in element.text:
                return element
            if id and element.id and id in element.id:
                return element
        return None
```

**Step 2: 编写测试**

```python
# backend/tests/test_android_driver.py
import pytest
from unittest.mock import AsyncMock, patch

from app.drivers.android import AndroidDriver


@pytest.fixture
def android_driver():
    return AndroidDriver("emulator-5554")


@pytest.mark.asyncio
async def test_android_driver_tap(android_driver):
    with patch.object(android_driver, '_run_adb', new_callable=AsyncMock) as mock_adb:
        mock_adb.return_value = (0, "", "")
        result = await android_driver.tap(100, 200)
        assert result is True
        mock_adb.assert_called_once_with("shell", "input", "tap", "100", "200")


@pytest.mark.asyncio
async def test_android_driver_swipe(android_driver):
    with patch.object(android_driver, '_run_adb', new_callable=AsyncMock) as mock_adb:
        mock_adb.return_value = (0, "", "")
        result = await android_driver.swipe(100, 500, 100, 100, 0.5)
        assert result is True
        mock_adb.assert_called_once()


@pytest.mark.asyncio
async def test_android_driver_input_text(android_driver):
    with patch.object(android_driver, '_run_adb', new_callable=AsyncMock) as mock_adb:
        mock_adb.return_value = (0, "", "")
        result = await android_driver.input_text("hello world")
        assert result is True
```

**Step 3: 运行测试**

```bash
cd backend
pytest tests/test_android_driver.py -v
```

**Step 4: Commit**

```bash
git add backend/app/drivers/android.py backend/tests/test_android_driver.py
git commit -m "feat(backend): add Android ADB driver implementation"
```

---

### Task 3.3: 实现 iOS XCTest 驱动

**Files:**
- Create: `backend/app/drivers/ios.py`
- Create: `backend/tests/test_ios_driver.py`

**Step 1: 创建 ios.py**

```python
import asyncio
import json
from io import BytesIO
from typing import Optional
from PIL import Image

from app.drivers.base import BaseDriver, Element, ElementType, DeviceInfo


class iOSDriver(BaseDriver):
    def __init__(self, serial: str, wda_url: str = "http://localhost:8100"):
        super().__init__(serial)
        self._wda_url = wda_url
        self._session_id = None

    async def _request(self, method: str, path: str, data: dict = None) -> dict:
        """发送 HTTP 请求到 WDA"""
        import httpx
        url = f"{self._wda_url}{path}"
        async with httpx.AsyncClient() as client:
            if method == "GET":
                response = await client.get(url)
            elif method == "POST":
                response = await client.post(url, json=data)
            elif method == "DELETE":
                response = await client.delete(url)
            else:
                raise ValueError(f"Unsupported method: {method}")
            return response.json()

    async def connect(self) -> bool:
        """连接设备"""
        try:
            result = await self._request("POST", "/session", {"capabilities": {}})
            self._session_id = result.get("sessionId")
            self._connected = True
            return True
        except Exception:
            return False

    async def disconnect(self) -> bool:
        """断开连接"""
        if self._session_id:
            try:
                await self._request("DELETE", f"/session/{self._session_id}")
            except Exception:
                pass
        self._connected = False
        return True

    async def get_device_info(self) -> DeviceInfo:
        """获取设备信息"""
        result = await self._request("GET", "/status")
        return DeviceInfo(
            name=result.get("name", "Unknown"),
            platform="ios",
            version=result.get("os", {}).get("version", "Unknown"),
            resolution=(result.get("width", 375), result.get("height", 812)),
            serial=self.serial
        )

    async def screenshot(self) -> Image.Image:
        """截取屏幕"""
        result = await self._request("GET", f"/session/{self._session_id}/screenshot")
        import base64
        image_data = base64.b64decode(result["value"])
        return Image.open(BytesIO(image_data))

    async def tap(self, x: int, y: int) -> bool:
        """点击坐标"""
        try:
            await self._request("POST", f"/session/{self._session_id}/wda/tap/0", {
                "x": x,
                "y": y
            })
            return True
        except Exception:
            return False

    async def swipe(self, start_x: int, start_y: int, end_x: int, end_y: int, duration: float = 0.3) -> bool:
        """滑动"""
        try:
            await self._request("POST", f"/session/{self._session_id}/wda/dragfromtoforduration", {
                "fromX": start_x,
                "fromY": start_y,
                "toX": end_x,
                "toY": end_y,
                "duration": duration
            })
            return True
        except Exception:
            return False

    async def input_text(self, text: str) -> bool:
        """输入文本"""
        try:
            await self._request("POST", f"/session/{self._session_id}/wda/keys", {
                "value": list(text)
            })
            return True
        except Exception:
            return False

    async def press_key(self, key: str) -> bool:
        """按键"""
        key_map = {
            "home": "home",
            "back": "home",
            "enter": "\n",
        }
        try:
            await self._request("POST", f"/session/{self._session_id}/wda/pressButton", {
                "name": key_map.get(key.lower(), key)
            })
            return True
        except Exception:
            return False

    async def get_elements(self) -> list[Element]:
        """获取元素树"""
        result = await self._request("GET", f"/session/{self._session_id}/source")
        return self._parse_source(result.get("value", ""))

    def _parse_source(self, xml_content: str) -> list[Element]:
        """解析 UI 源码"""
        import xml.etree.ElementTree as ET
        elements = []
        
        try:
            root = ET.fromstring(xml_content)
            for node in root.iter():
                bounds = (0, 0, 0, 0)
                if "x" in node.attrib:
                    bounds = (
                        int(node.attrib.get("x", 0)),
                        int(node.attrib.get("y", 0)),
                        int(node.attrib.get("width", 0)),
                        int(node.attrib.get("height", 0))
                    )
                
                element = Element(
                    id=node.attrib.get("identifier"),
                    text=node.attrib.get("value") or node.attrib.get("name"),
                    bounds=bounds,
                    element_type=ElementType.UNKNOWN,
                    attributes=node.attrib
                )
                elements.append(element)
        except ET.ParseError:
            pass
        
        return elements

    async def find_element(self, text: str = None, id: str = None) -> Optional[Element]:
        """查找元素"""
        elements = await self.get_elements()
        for element in elements:
            if text and element.text and text in element.text:
                return element
            if id and element.id and id in element.id:
                return element
        return None
```

**Step 2: 编写测试**

```python
# backend/tests/test_ios_driver.py
import pytest
from unittest.mock import AsyncMock, patch

from app.drivers.ios import iOSDriver


@pytest.fixture
def ios_driver():
    return iOSDriver("test-udid", "http://localhost:8100")


@pytest.mark.asyncio
async def test_ios_driver_connect(ios_driver):
    with patch.object(ios_driver, '_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = {"sessionId": "test-session"}
        result = await ios_driver.connect()
        assert result is True
        assert ios_driver._session_id == "test-session"


@pytest.mark.asyncio
async def test_ios_driver_tap(ios_driver):
    ios_driver._session_id = "test-session"
    with patch.object(ios_driver, '_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = {}
        result = await ios_driver.tap(100, 200)
        assert result is True
        mock_request.assert_called_once()
```

**Step 3: 运行测试**

```bash
cd backend
pytest tests/test_ios_driver.py -v
```

**Step 4: Commit**

```bash
git add backend/app/drivers/ios.py backend/tests/test_ios_driver.py
git commit -m "feat(backend): add iOS XCTest/WDA driver implementation"
```

---

## Phase 4: AI Agent 引擎

### Task 4.1: 实现 LLM 适配层

**Files:**
- Create: `backend/app/agent/llm/base.py`
- Create: `backend/app/agent/llm/openai.py`
- Create: `backend/app/agent/llm/factory.py`

**Step 1: 创建 llm/base.py**

```python
from abc import ABC, abstractmethod
from typing import AsyncIterator
from dataclasses import dataclass


@dataclass
class LLMMessage:
    role: str
    content: str


class BaseLLM(ABC):
    def __init__(self, model: str, api_key: str, base_url: str = None):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url

    @abstractmethod
    async def generate(self, messages: list[LLMMessage]) -> str:
        """生成响应"""
        pass

    @abstractmethod
    async def stream(self, messages: list[LLMMessage]) -> AsyncIterator[str]:
        """流式生成响应"""
        pass
```

**Step 2: 创建 llm/openai.py**

```python
from typing import AsyncIterator
from openai import AsyncOpenAI

from app.agent.llm.base import BaseLLM, LLMMessage


class OpenAILLM(BaseLLM):
    def __init__(self, model: str, api_key: str, base_url: str = None):
        super().__init__(model, api_key, base_url)
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    async def generate(self, messages: list[LLMMessage]) -> str:
        response = await self._client.chat.completions.create(
            model=self.model,
            messages=[{"role": m.role, "content": m.content} for m in messages]
        )
        return response.choices[0].message.content

    async def stream(self, messages: list[LLMMessage]) -> AsyncIterator[str]:
        stream = await self._client.chat.completions.create(
            model=self.model,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            stream=True
        )
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
```

**Step 3: 创建 llm/factory.py**

```python
from app.agent.llm.base import BaseLLM
from app.agent.llm.openai import OpenAILLM


def create_llm(provider: str, model: str, api_key: str, base_url: str = None) -> BaseLLM:
    """创建 LLM 实例"""
    factories = {
        "openai": OpenAILLM,
        "azure": OpenAILLM,
        "deepseek": OpenAILLM,
    }
    
    factory = factories.get(provider)
    if not factory:
        raise ValueError(f"Unsupported LLM provider: {provider}")
    
    return factory(model=model, api_key=api_key, base_url=base_url)
```

**Step 4: Commit**

```bash
git add backend/app/agent/llm/
git commit -m "feat(backend): add LLM adapter layer with OpenAI support"
```

---

### Task 4.2: 实现自然语言解析器

**Files:**
- Create: `backend/app/agent/parser.py`
- Create: `backend/tests/test_parser.py`

**Step 1: 创建 parser.py**

```python
from dataclasses import dataclass
from typing import Optional
import json

from app.agent.llm.base import BaseLLM, LLMMessage


@dataclass
class ParsedStep:
    action: str
    target: Optional[str]
    value: Optional[str]
    description: str


@dataclass
class ParsedTestCase:
    steps: list[ParsedStep]
    assertions: list[str]


PARSER_PROMPT = """你是一个测试用例解析器。将自然语言描述的测试步骤解析为结构化的动作列表。

可用的动作类型：
- tap: 点击元素，target 为元素描述
- swipe: 滑动，target 为方向 (up/down/left/right)
- input: 输入文本，target 为输入框描述，value 为输入内容
- wait: 等待，target 为等待条件
- verify: 验证，target 为验证内容
- press: 按键，target 为按键名称 (back/home/enter)

请将以下测试用例解析为 JSON 格式：
{"steps": [{"action": "动作", "target": "目标", "value": "值", "description": "描述"}], "assertions": ["断言描述"]}

测试用例：
{test_case}
"""


class TestCaseParser:
    def __init__(self, llm: BaseLLM):
        self.llm = llm

    async def parse(self, test_case: str) -> ParsedTestCase:
        """解析测试用例"""
        prompt = PARSER_PROMPT.format(test_case=test_case)
        response = await self.llm.generate([
            LLMMessage(role="user", content=prompt)
        ])
        
        return self._parse_response(response)

    def _parse_response(self, response: str) -> ParsedTestCase:
        """解析 LLM 响应"""
        try:
            data = json.loads(response)
            steps = [
                ParsedStep(
                    action=s.get("action", ""),
                    target=s.get("target"),
                    value=s.get("value"),
                    description=s.get("description", "")
                )
                for s in data.get("steps", [])
            ]
            return ParsedTestCase(steps=steps, assertions=data.get("assertions", []))
        except json.JSONDecodeError:
            return ParsedTestCase(steps=[], assertions=[])
```

**Step 2: 编写测试**

```python
# backend/tests/test_parser.py
import pytest
from unittest.mock import AsyncMock

from app.agent.parser import TestCaseParser, ParsedStep
from app.agent.llm.base import BaseLLM


@pytest.fixture
def mock_llm():
    llm = AsyncMock(spec=BaseLLM)
    return llm


@pytest.mark.asyncio
async def test_parser_parse_simple_case(mock_llm):
    mock_llm.generate.return_value = '''{
        "steps": [
            {"action": "tap", "target": "登录按钮", "value": null, "description": "点击登录按钮"},
            {"action": "input", "target": "用户名输入框", "value": "test@example.com", "description": "输入用户名"}
        ],
        "assertions": ["登录成功"]
    }'''
    
    parser = TestCaseParser(mock_llm)
    result = await parser.parse("点击登录按钮，输入用户名")
    
    assert len(result.steps) == 2
    assert result.steps[0].action == "tap"
    assert result.steps[1].value == "test@example.com"
    assert "登录成功" in result.assertions
```

**Step 3: 运行测试**

```bash
cd backend
pytest tests/test_parser.py -v
```

**Step 4: Commit**

```bash
git add backend/app/agent/parser.py backend/tests/test_parser.py
git commit -m "feat(backend): add natural language test case parser"
```

---

### Task 4.3: 实现动作执行器

**Files:**
- Create: `backend/app/agent/executor.py`
- Create: `backend/tests/test_executor.py`

**Step 1: 创建 executor.py**

```python
from dataclasses import dataclass
from typing import Optional
from enum import Enum

from app.drivers.base import BaseDriver, Element
from app.agent.parser import ParsedStep


class ExecutionResult(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class StepResult:
    step: ParsedStep
    result: ExecutionResult
    message: str
    screenshot: Optional[bytes] = None
    element: Optional[Element] = None


class ActionExecutor:
    def __init__(self, driver: BaseDriver):
        self.driver = driver

    async def execute(self, step: ParsedStep) -> StepResult:
        """执行单个步骤"""
        action_map = {
            "tap": self._execute_tap,
            "swipe": self._execute_swipe,
            "input": self._execute_input,
            "wait": self._execute_wait,
            "press": self._execute_press,
        }
        
        handler = action_map.get(step.action)
        if not handler:
            return StepResult(
                step=step,
                result=ExecutionResult.FAILED,
                message=f"Unknown action: {step.action}"
            )
        
        try:
            return await handler(step)
        except Exception as e:
            return StepResult(
                step=step,
                result=ExecutionResult.FAILED,
                message=str(e)
            )

    async def _execute_tap(self, step: ParsedStep) -> StepResult:
        """执行点击"""
        element = await self.driver.find_element(text=step.target, id=step.target)
        
        if element:
            x = element.bounds[0] + element.bounds[2] // 2
            y = element.bounds[1] + element.bounds[3] // 2
            success = await self.driver.tap(x, y)
        else:
            return StepResult(
                step=step,
                result=ExecutionResult.FAILED,
                message=f"Element not found: {step.target}"
            )
        
        return StepResult(
            step=step,
            result=ExecutionResult.SUCCESS if success else ExecutionResult.FAILED,
            message=f"Tapped on {step.target}",
            element=element
        )

    async def _execute_swipe(self, step: ParsedStep) -> StepResult:
        """执行滑动"""
        from PIL import Image
        screenshot = await self.driver.screenshot()
        width, height = screenshot.size
        
        direction = step.target.lower()
        if direction == "up":
            start_x, start_y = width // 2, height * 3 // 4
            end_x, end_y = width // 2, height // 4
        elif direction == "down":
            start_x, start_y = width // 2, height // 4
            end_x, end_y = width // 2, height * 3 // 4
        elif direction == "left":
            start_x, start_y = width * 3 // 4, height // 2
            end_x, end_y = width // 4, height // 2
        elif direction == "right":
            start_x, start_y = width // 4, height // 2
            end_x, end_y = width * 3 // 4, height // 2
        else:
            return StepResult(
                step=step,
                result=ExecutionResult.FAILED,
                message=f"Unknown swipe direction: {direction}"
            )
        
        success = await self.driver.swipe(start_x, start_y, end_x, end_y)
        return StepResult(
            step=step,
            result=ExecutionResult.SUCCESS if success else ExecutionResult.FAILED,
            message=f"Swiped {direction}"
        )

    async def _execute_input(self, step: ParsedStep) -> StepResult:
        """执行输入"""
        if step.target:
            element = await self.driver.find_element(text=step.target, id=step.target)
            if element:
                x = element.bounds[0] + element.bounds[2] // 2
                y = element.bounds[1] + element.bounds[3] // 2
                await self.driver.tap(x, y)
        
        success = await self.driver.input_text(step.value or "")
        return StepResult(
            step=step,
            result=ExecutionResult.SUCCESS if success else ExecutionResult.FAILED,
            message=f"Input: {step.value}"
        )

    async def _execute_wait(self, step: ParsedStep) -> StepResult:
        """执行等待"""
        import asyncio
        await asyncio.sleep(1)
        return StepResult(
            step=step,
            result=ExecutionResult.SUCCESS,
            message=f"Waited for {step.target}"
        )

    async def _execute_press(self, step: ParsedStep) -> StepResult:
        """执行按键"""
        success = await self.driver.press_key(step.target or "back")
        return StepResult(
            step=step,
            result=ExecutionResult.SUCCESS if success else ExecutionResult.FAILED,
            message=f"Pressed {step.target}"
        )
```

**Step 2: 编写测试**

```python
# backend/tests/test_executor.py
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.agent.executor import ActionExecutor, ExecutionResult
from app.agent.parser import ParsedStep
from app.drivers.base import BaseDriver, Element, ElementType


@pytest.fixture
def mock_driver():
    driver = AsyncMock(spec=BaseDriver)
    return driver


@pytest.mark.asyncio
async def test_execute_tap_success(mock_driver):
    mock_element = Element(
        id="btn-login",
        text="登录",
        bounds=(100, 200, 200, 50),
        element_type=ElementType.BUTTON,
        attributes={}
    )
    mock_driver.find_element.return_value = mock_element
    mock_driver.tap.return_value = True
    
    executor = ActionExecutor(mock_driver)
    step = ParsedStep(action="tap", target="登录", value=None, description="点击登录")
    result = await executor.execute(step)
    
    assert result.result == ExecutionResult.SUCCESS
    mock_driver.tap.assert_called_once()


@pytest.mark.asyncio
async def test_execute_input(mock_driver):
    mock_driver.tap.return_value = True
    mock_driver.input_text.return_value = True
    
    executor = ActionExecutor(mock_driver)
    step = ParsedStep(action="input", target=None, value="hello", description="输入文本")
    result = await executor.execute(step)
    
    assert result.result == ExecutionResult.SUCCESS
    mock_driver.input_text.assert_called_once_with("hello")
```

**Step 3: 运行测试**

```bash
cd backend
pytest tests/test_executor.py -v
```

**Step 4: Commit**

```bash
git add backend/app/agent/executor.py backend/tests/test_executor.py
git commit -m "feat(backend): add action executor for test steps"
```

---

## Phase 5: API 接口

### Task 5.1: 实现用例管理 API

**Files:**
- Create: `backend/app/api/v1/cases.py`
- Create: `backend/app/schemas/case.py`

**Step 1: 创建 schemas/case.py**

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class TestCaseCreate(BaseModel):
    project_id: int
    name: str
    description: Optional[str] = None
    steps: list[dict] = []
    assertions: list[str] = []
    tags: list[str] = []


class TestCaseUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    steps: Optional[list[dict]] = None
    assertions: Optional[list[str]] = None
    tags: Optional[list[str]] = None


class TestCaseResponse(BaseModel):
    id: int
    project_id: int
    name: str
    description: Optional[str]
    steps: list[dict]
    assertions: list[str]
    tags: list[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
```

**Step 2: 创建 api/v1/cases.py**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.case import TestCase, TestProject
from app.schemas.case import TestCaseCreate, TestCaseUpdate, TestCaseResponse

router = APIRouter(prefix="/cases", tags=["cases"])


@router.post("/", response_model=TestCaseResponse)
async def create_case(case: TestCaseCreate, db: AsyncSession = Depends(get_db)):
    project = await db.get(TestProject, case.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    db_case = TestCase(**case.model_dump())
    db.add(db_case)
    await db.commit()
    await db.refresh(db_case)
    return db_case


@router.get("/{case_id}", response_model=TestCaseResponse)
async def get_case(case_id: int, db: AsyncSession = Depends(get_db)):
    case = await db.get(TestCase, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


@router.get("/", response_model=list[TestCaseResponse])
async def list_cases(project_id: int = None, db: AsyncSession = Depends(get_db)):
    query = select(TestCase)
    if project_id:
        query = query.where(TestCase.project_id == project_id)
    result = await db.execute(query)
    return result.scalars().all()


@router.put("/{case_id}", response_model=TestCaseResponse)
async def update_case(case_id: int, case: TestCaseUpdate, db: AsyncSession = Depends(get_db)):
    db_case = await db.get(TestCase, case_id)
    if not db_case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    for key, value in case.model_dump(exclude_unset=True).items():
        setattr(db_case, key, value)
    
    await db.commit()
    await db.refresh(db_case)
    return db_case


@router.delete("/{case_id}")
async def delete_case(case_id: int, db: AsyncSession = Depends(get_db)):
    case = await db.get(TestCase, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    await db.delete(case)
    await db.commit()
    return {"message": "Case deleted"}
```

**Step 3: 注册路由到 main.py**

```python
from app.api.v1 import cases

app.include_router(cases.router, prefix="/api/v1")
```

**Step 4: Commit**

```bash
git add backend/app/api/v1/cases.py backend/app/schemas/
git commit -m "feat(backend): add test case management API"
```

---

### Task 5.2: 实现执行 API

**Files:**
- Create: `backend/app/api/v1/executions.py`
- Create: `backend/app/schemas/execution.py`

**Step 1: 创建 schemas/execution.py**

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ExecutionCreate(BaseModel):
    case_id: int
    device_id: int
    llm_config_id: int


class ExecutionResponse(BaseModel):
    id: int
    case_id: int
    device_id: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
```

**Step 2: 创建 api/v1/executions.py**

```python
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.execution import TestExecution, ExecutionStatus
from app.models.device import Device, DeviceStatus
from app.models.llm_config import LLMConfig
from app.schemas.execution import ExecutionCreate, ExecutionResponse
from app.agent.parser import TestCaseParser
from app.agent.executor import ActionExecutor
from app.agent.llm.factory import create_llm
from app.drivers.android import AndroidDriver
from app.drivers.ios import iOSDriver

router = APIRouter(prefix="/executions", tags=["executions"])


@router.post("/", response_model=ExecutionResponse)
async def create_execution(execution: ExecutionCreate, db: AsyncSession = Depends(get_db)):
    device = await db.get(Device, execution.device_id)
    if not device or device.status != DeviceStatus.ONLINE:
        raise HTTPException(status_code=400, detail="Device not available")
    
    db_execution = TestExecution(**execution.model_dump())
    db.add(db_execution)
    await db.commit()
    await db.refresh(db_execution)
    return db_execution


@router.get("/{execution_id}", response_model=ExecutionResponse)
async def get_execution(execution_id: int, db: AsyncSession = Depends(get_db)):
    execution = await db.get(TestExecution, execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    return execution


@router.post("/{execution_id}/start")
async def start_execution(execution_id: int, db: AsyncSession = Depends(get_db)):
    execution = await db.get(TestExecution, execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    
    execution.status = ExecutionStatus.RUNNING
    await db.commit()
    
    return {"message": "Execution started", "execution_id": execution_id}


@router.websocket("/ws/{execution_id}")
async def execution_websocket(websocket: WebSocket, execution_id: int):
    await websocket.accept()
    
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Received: {data}")
    except WebSocketDisconnect:
        pass
```

**Step 3: Commit**

```bash
git add backend/app/api/v1/executions.py backend/app/schemas/execution.py
git commit -m "feat(backend): add execution API with WebSocket support"
```

---

## Phase 6: 前端页面

### Task 6.1: 实现前端布局

**Files:**
- Create: `frontend/src/components/Layout/MainLayout.tsx`
- Create: `frontend/src/components/Layout/Sidebar.tsx`
- Create: `frontend/src/App.tsx`

**Step 1: 创建 MainLayout.tsx**

```tsx
import React from 'react';
import { Layout, Menu } from 'antd';
import {
  DashboardOutlined,
  FileTextOutlined,
  PlayCircleOutlined,
  MobileOutlined,
  BarChartOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';

const { Sider, Content } = Layout;

const menuItems = [
  { key: '/', icon: <DashboardOutlined />, label: '仪表盘' },
  { key: '/cases', icon: <FileTextOutlined />, label: '用例管理' },
  { key: '/executions', icon: <PlayCircleOutlined />, label: '执行中心' },
  { key: '/devices', icon: <MobileOutlined />, label: '设备管理' },
  { key: '/reports', icon: <BarChartOutlined />, label: '测试报告' },
  { key: '/settings', icon: <SettingOutlined />, label: '系统设置' },
];

export const MainLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const navigate = useNavigate();
  const location = useLocation();

  return (
    <Layout className="min-h-screen">
      <Sider
        theme="dark"
        style={{ background: '#161B22' }}
        width={220}
      >
        <div className="h-16 flex items-center justify-center border-b border-gray-700">
          <span className="text-xl font-display text-accent-primary">MOBILE TEST AI</span>
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
          style={{ background: 'transparent' }}
        />
      </Sider>
      <Layout>
        <Content className="p-6 bg-background-primary">
          {children}
        </Content>
      </Layout>
    </Layout>
  );
};
```

**Step 2: 更新 App.tsx**

```tsx
import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import { MainLayout } from './components/Layout/MainLayout';

const Dashboard = React.lazy(() => import('./pages/Dashboard'));
const Cases = React.lazy(() => import('./pages/Cases'));
const Executions = React.lazy(() => import('./pages/Executions'));
const Devices = React.lazy(() => import('./pages/Devices'));
const Reports = React.lazy(() => import('./pages/Reports'));
const Settings = React.lazy(() => import('./pages/Settings'));

function App() {
  return (
    <ConfigProvider
      theme={{
        token: {
          colorPrimary: '#00FFD1',
          colorBgContainer: '#161B22',
          colorText: '#F0F6FC',
        },
      }}
    >
      <BrowserRouter>
        <MainLayout>
          <React.Suspense fallback={<div>Loading...</div>}>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/cases" element={<Cases />} />
              <Route path="/executions" element={<Executions />} />
              <Route path="/devices" element={<Devices />} />
              <Route path="/reports" element={<Reports />} />
              <Route path="/settings" element={<Settings />} />
            </Routes>
          </React.Suspense>
        </MainLayout>
      </BrowserRouter>
    </ConfigProvider>
  );
}

export default App;
```

**Step 3: Commit**

```bash
git add frontend/src/components/Layout/ frontend/src/App.tsx
git commit -m "feat(frontend): add main layout with sidebar navigation"
```

---

### Task 6.2: 实现仪表盘页面

**Files:**
- Create: `frontend/src/pages/Dashboard/index.tsx`
- Create: `frontend/src/components/Dashboard/StatCard.tsx`

**Step 1: 创建 StatCard.tsx**

```tsx
import React from 'react';
import { Card, Statistic } from 'antd';

interface StatCardProps {
  title: string;
  value: number;
  suffix?: string;
  prefix?: React.ReactNode;
  color?: string;
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  suffix,
  prefix,
  color = '#00FFD1',
}) => {
  return (
    <Card
      className="bg-background-secondary border-gray-700"
      styles={{ body: { padding: '20px' } }}
    >
      <Statistic
        title={<span className="text-text-secondary">{title}</span>}
        value={value}
        suffix={suffix}
        prefix={prefix}
        valueStyle={{ color, fontSize: '32px', fontWeight: 'bold' }}
      />
    </Card>
  );
};
```

**Step 2: 创建 Dashboard/index.tsx**

```tsx
import React from 'react';
import { Row, Col, Card } from 'antd';
import {
  FileTextOutlined,
  PlayCircleOutlined,
  MobileOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';
import { StatCard } from '../../components/Dashboard/StatCard';

const Dashboard: React.FC = () => {
  return (
    <div>
      <h1 className="text-2xl font-display mb-6 text-text-primary">仪表盘</h1>
      
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <StatCard
            title="测试用例"
            value={128}
            prefix={<FileTextOutlined />}
          />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <StatCard
            title="今日执行"
            value={47}
            prefix={<PlayCircleOutlined />}
            color="#7B61FF"
          />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <StatCard
            title="设备在线"
            value={12}
            prefix={<MobileOutlined />}
            color="#3FB950"
          />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <StatCard
            title="通过率"
            value={99.2}
            suffix="%"
            prefix={<CheckCircleOutlined />}
            color="#00FFD1"
          />
        </Col>
      </Row>

      <Row gutter={[16, 16]} className="mt-6">
        <Col xs={24} lg={16}>
          <Card
            title="最近执行"
            className="bg-background-secondary border-gray-700"
          >
            <div className="text-text-secondary">暂无数据</div>
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card
            title="设备状态"
            className="bg-background-secondary border-gray-700"
          >
            <div className="text-text-secondary">暂无数据</div>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Dashboard;
```

**Step 3: Commit**

```bash
git add frontend/src/pages/Dashboard/ frontend/src/components/Dashboard/
git commit -m "feat(frontend): add dashboard page with stat cards"
```

---

## Phase 7: Docker 部署

### Task 7.1: 创建 Docker 配置

**Files:**
- Create: `docker-compose.yml`
- Create: `backend/Dockerfile`
- Create: `frontend/Dockerfile`

**Step 1: 创建 docker-compose.yml**

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: mobile_test
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7
    ports:
      - "6379:6379"

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8088:8088"
    environment:
      DATABASE_URL: postgresql+asyncpg://postgres:postgres@postgres:5432/mobile_test
      REDIS_URL: redis://redis:6379/0
    depends_on:
      - postgres
      - redis

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "80:80"
    depends_on:
      - backend

volumes:
  postgres_data:
```

**Step 2: 创建 backend/Dockerfile**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8088

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8088"]
```

**Step 3: 创建 frontend/Dockerfile**

```dockerfile
FROM node:18-alpine as builder

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

**Step 4: Commit**

```bash
git add docker-compose.yml backend/Dockerfile frontend/Dockerfile
git commit -m "feat: add Docker configuration for deployment"
```

---

## 执行选项

计划完成并保存到 `docs/plans/2026-02-12-mobile-test-platform-implementation.md`。

**两种执行方式：**

1. **Subagent-Driven (当前会话)** - 每个任务派发独立子代理，任务间进行代码审查，快速迭代

2. **Parallel Session (独立会话)** - 在新会话中使用 executing-plans，批量执行并设置检查点

**选择哪种方式？**
