from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models import TestExecution, ExecutionStatus, TestCase, Device
from app.schemas import ExecutionCreate, ExecutionUpdate, ExecutionResponse, ExecutionDetailResponse

router = APIRouter(prefix="/executions", tags=["执行管理"])


@router.get("", response_model=List[ExecutionResponse])
async def list_executions(
    skip: int = 0,
    limit: int = 100,
    status: ExecutionStatus = None,
    test_case_id: int = None,
    device_id: int = None,
    db: AsyncSession = Depends(get_db)
):
    query = select(TestExecution).offset(skip).limit(limit)
    
    if status:
        query = query.where(TestExecution.status == status)
    if test_case_id:
        query = query.where(TestExecution.test_case_id == test_case_id)
    if device_id:
        query = query.where(TestExecution.device_id == device_id)
    
    result = await db.execute(query.order_by(TestExecution.created_at.desc()))
    executions = result.scalars().all()
    return executions


@router.get("/{execution_id}", response_model=ExecutionResponse)
async def get_execution(execution_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TestExecution).where(TestExecution.id == execution_id))
    execution = result.scalar_one_or_none()
    if not execution:
        raise HTTPException(status_code=404, detail="执行记录不存在")
    return execution


@router.post("", response_model=ExecutionResponse, status_code=status.HTTP_201_CREATED)
async def create_execution(
    execution: ExecutionCreate,
    user_id: int = 1,
    db: AsyncSession = Depends(get_db)
):
    case_result = await db.execute(select(TestCase).where(TestCase.id == execution.test_case_id))
    case = case_result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="测试用例不存在")
    
    device_result = await db.execute(select(Device).where(Device.id == execution.device_id))
    device = device_result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")
    
    db_execution = TestExecution(
        test_case_id=execution.test_case_id,
        device_id=execution.device_id,
        user_id=user_id,
        status=ExecutionStatus.PENDING,
        started_at=datetime.utcnow(),
    )
    db.add(db_execution)
    await db.commit()
    await db.refresh(db_execution)
    return db_execution


@router.patch("/{execution_id}", response_model=ExecutionResponse)
async def update_execution(
    execution_id: int,
    execution_update: ExecutionUpdate,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(TestExecution).where(TestExecution.id == execution_id))
    execution = result.scalar_one_or_none()
    if not execution:
        raise HTTPException(status_code=404, detail="执行记录不存在")
    
    update_data = execution_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(execution, key, value)
    
    if execution.status in [ExecutionStatus.SUCCESS, ExecutionStatus.FAILED, ExecutionStatus.CANCELLED]:
        execution.finished_at = datetime.utcnow()
        if execution.started_at:
            execution.duration = (execution.finished_at - execution.started_at).total_seconds()
    
    await db.commit()
    await db.refresh(execution)
    return execution


@router.delete("/{execution_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_execution(execution_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TestExecution).where(TestExecution.id == execution_id))
    execution = result.scalar_one_or_none()
    if not execution:
        raise HTTPException(status_code=404, detail="执行记录不存在")
    
    await db.delete(execution)
    await db.commit()
    return None
