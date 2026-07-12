from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db import get_db_session
from app.models import User, Project, ProjectStatus
from app.schemas import ProjectCreate, ProjectUpdate, ProjectResponse
from app.dependencies import get_current_user

router = APIRouter(prefix="/projects", tags=["projects"])

@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Create a new project for the authenticated user."""
    new_project = Project(
        owner_id=current_user.id,
        title=payload.title,
        description=payload.description,
        status=payload.status
    )
    db.add(new_project)
    await db.commit()
    await db.refresh(new_project)
    return new_project

@router.get("", response_model=List[ProjectResponse])
async def list_projects(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status_filter: Optional[ProjectStatus] = Query(default=None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """List active (non-soft-deleted) projects for the user with pagination and optional status filter."""
    stmt = select(Project).where(
        Project.owner_id == current_user.id,
        Project.deleted_at.is_(None)
    )
    
    if status_filter:
        stmt = stmt.where(Project.status == status_filter)
        
    stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(stmt)
    projects = result.scalars().all()
    return projects

@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Retrieve details for a specific active project owned by the user."""
    stmt = select(Project).where(
        Project.id == project_id,
        Project.owner_id == current_user.id,
        Project.deleted_at.is_(None)
    )
    result = await db.execute(stmt)
    project = result.scalars().first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    return project

@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    payload: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Update details of a project owned by the user."""
    stmt = select(Project).where(
        Project.id == project_id,
        Project.owner_id == current_user.id,
        Project.deleted_at.is_(None)
    )
    result = await db.execute(stmt)
    project = result.scalars().first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    # Perform updates
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)
        
    await db.commit()
    await db.refresh(project)
    return project

@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Soft delete a project and its tasks by setting deleted_at."""
    stmt = select(Project).where(
        Project.id == project_id,
        Project.owner_id == current_user.id,
        Project.deleted_at.is_(None)
    )
    result = await db.execute(stmt)
    project = result.scalars().first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    now_utc = datetime.now(timezone.utc)
    project.deleted_at = now_utc
    
    # Eagerly load tasks to soft-delete them as well
    # Wait, the cascade delete in models works for DB-level deletions, but since this is a soft delete
    # we should manually soft-delete the linked tasks so they also disappear from task list queries!
    from app.models import Task
    task_stmt = select(Task).where(
        Task.project_id == project_id,
        Task.deleted_at.is_(None)
    )
    tasks_res = await db.execute(task_stmt)
    tasks = tasks_res.scalars().all()
    for task in tasks:
        task.deleted_at = now_utc

    await db.commit()
    return None
