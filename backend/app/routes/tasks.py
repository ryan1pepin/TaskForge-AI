"""Task CRUD + AI endpoints."""
from __future__ import annotations
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.ai.integration import call_llm
from app.db import get_db_session
from app.dependencies import get_current_user
from app.models import Project, Task, User, TaskStatus
from app.schemas import (
    AIPriorityResponse, AIDeadlineResponse, AIDescriptionResponse,
    AISuggestionItem, AISuggestedTasksResponse, HealthScoreResponse,
    HealthTask, TaskCreate, TaskUpdate, TaskResponse,
)

router = APIRouter(prefix="/projects", tags=["tasks"])

async def verify_owner(project_id: UUID, user_id: UUID, db: AsyncSession) -> Project:
    """Project exists, belongs to user, not soft-deleted."""
    p = (await db.execute(select(Project).where(
        Project.id == project_id,
        Project.owner_id == user_id,
        Project.deleted_at.is_(None),
    ))).scalars().first()
    if not p:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found or access denied")
    return p

# ── CRUD ───────────────────────────────────────────────────────────────────────

@router.post("/{project_id}/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(project_id: UUID, body: TaskCreate,
                      user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db_session)):
    await verify_owner(project_id, user.id, db)
    t = Task(project_id=project_id, **body.model_dump())
    db.add(t); await db.commit(); await db.refresh(t)
    return t

@router.get("/{project_id}/tasks", response_model=List[TaskResponse])
async def list_tasks(project_id: UUID, status_f: Optional[TaskStatus] = Query(None, alias="status"),
                     user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db_session)):
    await verify_owner(project_id, user.id, db)
    q = select(Task).where(Task.project_id == project_id, Task.deleted_at.is_(None))
    if status_f: q = q.where(Task.status == status_f)
    return (await db.execute(q.order_by(Task.order_index.asc()))).scalars().all()

@router.patch("/{project_id}/tasks/{task_id}", response_model=TaskResponse)
async def update_task(project_id: UUID, task_id: UUID, body: TaskUpdate,
                      user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db_session)):
    await verify_owner(project_id, user.id, db)
    t = (await db.execute(select(Task).where(Task.id == task_id, Task.project_id == project_id, Task.deleted_at.is_(None)))).scalars().first()
    if not t: raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
    for k, v in body.model_dump(exclude_unset=True).items(): setattr(t, k, v)
    await db.commit(); await db.refresh(t)
    return t

@router.delete("/{project_id}/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(project_id: UUID, task_id: UUID,
                      user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db_session)):
    await verify_owner(project_id, user.id, db)
    t = (await db.execute(select(Task).where(Task.id == task_id, Task.project_id == project_id, Task.deleted_at.is_(None)))).scalars().first()
    if not t: raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
    t.deleted_at = datetime.now(timezone.utc)
    await db.commit()

# ── AI Suggestion Endpoints ────────────────────────────────────────────────────

@router.post("/{project_id}/tasks/{task_id}/suggest-priority", response_model=AIPriorityResponse)
async def suggest_priority(project_id: UUID, task_id: UUID,
                           user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db_session)):
    """Ask LLM to analyze project context and suggest a priority for this new task."""
    proj = await verify_owner(project_id, user.id, db)
    t = (await db.execute(select(Task).where(Task.id == task_id, Task.project_id == project_id, Task.deleted_at.is_(None)))).scalars().first()
    if not t: raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")

    # Pull sibling tasks for context: (title, priority, status)
    siblings = [f"{tk.title} (p:{tk.priority}, {tk.status})" for tk in (
        await db.execute(select(Task).where(Task.project_id == project_id, Task.id != task_id, Task.deleted_at.is_(None)))
    )].scalars().all()

    try:
        txt = await call_llm("You are a concise, strictly factual project manager.", {
            "project_title": proj.title,
            "project_desc": proj.description or "(no description)",
            "task_title": t.title,
            "task_body": t.description or "",
            "sibling_tasks": (("\n".join(siblings))[:4096] if siblings else "No other tasks yet."),
        })
        import json; d = json.loads(txt)
        return AIPriorityResponse(
            suggested_priority=int(d.get("suggested_priority", 2)),
            reasoning=d.get("reasoning", ""),
            confidence=min(max(float(d.get("confidence", .5)), 0), 1.0),
        )
    except Exception:
        return AIPriorityResponse(suggested_priority=2, reasoning="Unable to analyze (LLM unavailable) — default set to Medium.", confidence=0.0)

@router.post("/{project_id}/tasks/{task_id}/suggest-deadline", response_model=AIDeadlineResponse)
async def suggest_deadline(project_id: UUID, task_id: UUID,
                           user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db_session)):
    proj = await verify_owner(project_id, user.id, db)
    t = (await db.execute(select(Task).where(Task.id == task_id, Task.project_id == project_id, Task.deleted_at.is_(None)))).scalars().first()
    if not t: raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")

    try:
        txt = await call_llm("You are a concise PM assistant.", {
            "project_title": proj.title,
            "task_title": t.title,
            "task_body": t.description or "",
        })
        import json; d = json.loads(txt)
        return AIDeadlineResponse(
            suggested_due_date=d.get("suggested_due_date"),
            confidence=min(max(float(d.get("confidence", .5)), 0), 1.0),
            reasoning=d.get("reasoning", ""),
        )
    except Exception:
        return AIDeadlineResponse(confidence=0.0, reasoning="Unable to detect deadline cues.")

@router.post("/{project_id}/tasks/{task_id}/generate-description", response_model=AIDescriptionResponse)
async def generate_description(project_id: UUID, task_id: UUID,
                               user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db_session)):
    proj = await verify_owner(project_id, user.id, db)
    t = (await db.execute(select(Task).where(Task.id == task_id, Task.project_id == project_id, Task.deleted_at.is_(None)))).scalars().first()
    if not t: raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")

    try:
        txt = await call_llm("You are an expert technical PM.", {
            "project_title": proj.title,
            "project_desc": proj.description or "",
            "task_title": t.title,
        }, response_json=False)
        return AIDescriptionResponse(description=txt[:500], confidence=1.0)
    except Exception:
        return AIDescriptionResponse(description="LLM unavailable — write description manually.", confidence=0.0)

@router.post("/{project_id}/suggest-tasks", response_model=AISuggestedTasksResponse)
async def suggest_tasks(project_id: UUID,
                        user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db_session)):
    proj = await verify_owner(project_id, user.id, db)

    try:
        txt = await call_llm("You are a project management assistant.", {
            "project_title": proj.title,
            "project_desc": proj.description or "",
        })
        import json; d = json.loads(txt)
        if isinstance(d, dict): d = d.get("suggestions", [])
        items = []
        for item in (d[:10] if isinstance(d, list) else []):
            if isinstance(item, str):
                items.append(AISuggestionItem(title=item))
            elif isinstance(item, dict):
                items.append(AISuggestionItem(
                    title=item.get("title", "Untitled"),
                    description=item.get("description"),
                    priority=min(max(int(item.get("priority", 0)), 0), 3)
                ))
        return AISuggestedTasksResponse(suggestions=items)
    except Exception:
        return AISuggestedTasksResponse(suggestions=[])

@router.get("/{project_id}/health", response_model=HealthScoreResponse)
async def project_health(project_id: UUID,
                         user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db_session)):
    """Compute an anomaly-detection style health score for this project."""
    proj = await verify_owner(project_id, user.id, db)

    all_tasks = (await db.execute(select(Task).where(
        Task.project_id == project_id, Task.deleted_at.is_(None)
    ))).scalars().all()
    total = len(all_tasks) or 1
    done_n = sum(1 for tk in all_tasks if tk.status == TaskStatus.DONE)
    progress = round(done_n / total * 100, 1)
    overdue = sum(1 for tk in all_tasks if tk.due_date and datetime.now(timezone.utc) > tk.due_date and tk.status != TaskStatus.DONE)
    high_pri_open = sum(1 for tk in all_tasks if tk.priority >= 2 and tk.status != TaskStatus.DONE)

    score = max(0, min(10, round(
        (progress / 10) * 5 +
        max(0, 5 - overdue * 1.5) +
        max(0, 5 - high_pri_open),
    )))
    flags = [(f"Flag: {overdue} overdue tasks") if overdue else "" for _ in ()][0] if overdue else None

    ts_list = [HealthTask(task=tr.title, status=str(tr.status.value), priority=int(tr.priority))
               for tr in all_tasks[:20]]
    return HealthScoreResponse(
        score=int(score), progress_pct=float(progress),
        total=total, completed=done_n, overdue_count=overdue,
        high_prio_open=high_pri_open, flag=flags,
        recent_tasks=ts_list, project_title=proj.title,
    )

