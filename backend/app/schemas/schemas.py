from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, Field
from app.models import (
    UserStatus, DeviceStatus, DevicePlatform, 
    CaseStatus, ExecutionStatus
)


class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$')
    full_name: Optional[str] = None


class UserCreate(UserBase):
    password: str = Field(..., min_length=6)


class UserUpdate(BaseModel):
    email: Optional[str] = Field(None, pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$')
    full_name: Optional[str] = None
    status: Optional[UserStatus] = None


class UserResponse(UserBase):
    id: int
    status: UserStatus
    is_superuser: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DeviceBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    platform: DevicePlatform
    device_id: str = Field(..., min_length=1, max_length=100)
    version: Optional[str] = None
    model: Optional[str] = None
    manufacturer: Optional[str] = None
    screen_resolution: Optional[str] = None


class DeviceCreate(DeviceBase):
    capabilities: Optional[dict] = {}


class DeviceUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[DeviceStatus] = None
    version: Optional[str] = None
    model: Optional[str] = None
    manufacturer: Optional[str] = None
    screen_resolution: Optional[str] = None
    capabilities: Optional[dict] = None


class DeviceResponse(DeviceBase):
    id: int
    status: DeviceStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TestCaseBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    content: str = Field(..., min_length=1)
    tags: Optional[List[str]] = []


class TestCaseCreate(TestCaseBase):
    pass


class TestCaseUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[List[str]] = None
    status: Optional[CaseStatus] = None


class TestCaseResponse(TestCaseBase):
    id: int
    status: CaseStatus
    creator_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ExecutionBase(BaseModel):
    test_case_id: int
    device_id: int


class ExecutionCreate(ExecutionBase):
    pass


class ExecutionUpdate(BaseModel):
    status: Optional[ExecutionStatus] = None
    result: Optional[str] = None
    error_message: Optional[str] = None
    screenshot_urls: Optional[List[str]] = None
    video_url: Optional[str] = None
    logs: Optional[str] = None


class ExecutionResponse(ExecutionBase):
    id: int
    user_id: int
    status: ExecutionStatus
    result: Optional[str] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    duration: Optional[float] = None
    screenshot_urls: Optional[List[str]] = None
    video_url: Optional[str] = None
    logs: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ExecutionDetailResponse(ExecutionResponse):
    steps: List[Any] = []
