from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models import TestCase, CaseStatus
from app.schemas import TestCaseCreate, TestCaseUpdate, TestCaseResponse

router = APIRouter(prefix="/cases", tags=["用例管理"])


@router.get("", response_model=List[TestCaseResponse])
async def list_cases(
    skip: int = 0,
    limit: int = 100,
    status: CaseStatus = None,
    db: AsyncSession = Depends(get_db)
):
    query = select(TestCase).offset(skip).limit(limit)
    if status:
        query = query.where(TestCase.status == status)
    
    result = await db.execute(query)
    cases = result.scalars().all()
    return cases


@router.get("/{case_id}", response_model=TestCaseResponse)
async def get_case(case_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TestCase).where(TestCase.id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="用例不存在")
    return case


@router.post("", response_model=TestCaseResponse, status_code=status.HTTP_201_CREATED)
async def create_case(
    case: TestCaseCreate,
    creator_id: int = 1,
    db: AsyncSession = Depends(get_db)
):
    db_case = TestCase(
        name=case.name,
        description=case.description,
        content=case.content,
        tags=case.tags,
        status=CaseStatus.DRAFT,
        creator_id=creator_id,
    )
    db.add(db_case)
    await db.commit()
    await db.refresh(db_case)
    return db_case


@router.patch("/{case_id}", response_model=TestCaseResponse)
async def update_case(
    case_id: int,
    case_update: TestCaseUpdate,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(TestCase).where(TestCase.id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="用例不存在")
    
    update_data = case_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(case, key, value)
    
    await db.commit()
    await db.refresh(case)
    return case


@router.delete("/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_case(case_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TestCase).where(TestCase.id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="用例不存在")
    
    await db.delete(case)
    await db.commit()
    return None
