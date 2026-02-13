from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text, 
    ForeignKey, Enum, Float, JSON
)
from sqlalchemy.orm import relationship, declarative_base
import enum

Base = declarative_base()


class UserStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class DeviceStatus(str, enum.Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    BUSY = "busy"
    ERROR = "error"


class DevicePlatform(str, enum.Enum):
    ANDROID = "android"
    IOS = "ios"


class CaseStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class ExecutionStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100))
    status = Column(Enum(UserStatus), default=UserStatus.ACTIVE)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    devices = relationship("Device", back_populates="owner")
    test_cases = relationship("TestCase", back_populates="creator")
    executions = relationship("TestExecution", back_populates="user")


class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    platform = Column(Enum(DevicePlatform), nullable=False)
    device_id = Column(String(100), unique=True, nullable=False, index=True)
    status = Column(Enum(DeviceStatus), default=DeviceStatus.OFFLINE)
    version = Column(String(50))
    model = Column(String(100))
    manufacturer = Column(String(100))
    screen_resolution = Column(String(50))
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    capabilities = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User", back_populates="devices")
    executions = relationship("TestExecution", back_populates="device")


class TestCase(Base):
    __tablename__ = "test_cases"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, index=True)
    description = Column(Text)
    status = Column(Enum(CaseStatus), default=CaseStatus.DRAFT)
    content = Column(JSON, nullable=False)
    tags = Column(JSON, default=list)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    creator = relationship("User", back_populates="test_cases")
    executions = relationship("TestExecution", back_populates="test_case")


class TestExecution(Base):
    __tablename__ = "test_executions"

    id = Column(Integer, primary_key=True, index=True)
    test_case_id = Column(Integer, ForeignKey("test_cases.id"), nullable=False)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(Enum(ExecutionStatus), default=ExecutionStatus.PENDING)
    result = Column(JSON, default=dict)
    error_message = Column(Text)
    started_at = Column(DateTime)
    finished_at = Column(DateTime)
    duration = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

    test_case = relationship("TestCase", back_populates="executions")
    device = relationship("Device", back_populates="executions")
    user = relationship("User", back_populates="executions")
    steps = relationship("ExecutionStep", back_populates="execution", cascade="all, delete-orphan")


class ExecutionStep(Base):
    __tablename__ = "execution_steps"

    id = Column(Integer, primary_key=True, index=True)
    execution_id = Column(Integer, ForeignKey("test_executions.id"), nullable=False)
    step_number = Column(Integer, nullable=False)
    action = Column(String(50), nullable=False)
    target = Column(Text)
    params = Column(JSON, default=dict)
    result = Column(JSON, default=dict)
    screenshot = Column(String(500))
    duration = Column(Float)
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    execution = relationship("TestExecution", back_populates="steps")
