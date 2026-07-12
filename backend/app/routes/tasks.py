from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db import get_db_session
from app.models import User, Project, Task, TaskStatus
from app.schemas import TaskCreate, TaskUpdate, TaskResponse
from app.dependencies import get_current_user

router = APIRouter(prefix="/projects", tags=["tasks"])

async def verify_project_ownership(project_id: UUID, user_id: UUID, db: AsyncSession) -> Project:
    """Helper to verify a project exists, belongs to the user, and is not soft deleted."""
    stmt = select(Project).where(
        Project.id == project_id,
        Project.owner_id == user_id,
        Project.deleted_at.is_(None)
    )
    result = await db.execute(stmt)
    project = result.scalars().first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or access denied"
        )
    return project

@router.post("/{project_id}/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    project_id: UUID,
    payload: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Create a task within a project, verifying project ownership."""
    await verify_project_ownership(project_id, current_user.id, db)
    
    new_task = Task(
        project_id=project_id,
        title=payload.title,
        description=payload.description,
        status=payload.status,
        priority=payload.priority,
        order_index=payload.order_index,
        due_date=payload.due_date
    )
    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)
    return new_task

@router.get("/{project_id}/tasks", response_model=List[TaskResponse])
async def list_tasks(
    project_id: UUID,
    status_filter: Optional[TaskStatus] = Query(default=None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """List active (non-soft-deleted) tasks for a project, sorted by order_index."""
    await verify_project_ownership(project_id, current_user.id, db)

    stmt = select(Task).where(
        Task.project_id == project_id,
        Task.deleted_at.is_(None)
    )
    
    if status_filter:
        stmt = stmt.where(Task.status == status_filter)
        
    # Order by order_index ascending
    stmt = stmt.order_by(Task.order_index.asc())
    
    result = await db.execute(stmt)
    tasks = result.scalars().all()
    return tasks

@router.patch("/{project_id}/tasks/{task_id}", response_model=TaskResponse)
async def update_task(
    project_id: UUID,
    task_id: UUID,
    payload: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Update details of a task inside a user-owned project."""
    await verify_project_ownership(project_id, current_user.id, db)

    stmt = select(Task).where(
        Task.id == task_id,
        Task.project_id == project_id,
        Task.deleted_at.is_(None)
    )
    result = await db.execute(stmt)
    task = result.scalars().first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    # Perform updates
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)
        
    await db.commit()
    await db.refresh(task)
    return task

@router.delete("/{project_id}/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    project_id: UUID,
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Soft delete a task by setting its deleted_at timestamp."""
    await verify_project_ownership(project_id, current_user.id, db)

    stmt = select(Task).where(
        Task.id == task_id,
        Task.project_id == project_id,
        Task.deleted_at.is_(None)
    )
    result = await db.execute(stmt)
    task = result.scalars().first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    task.deleted_at = datetime.now(timezone.utc)
    await db.commit()
    return None
