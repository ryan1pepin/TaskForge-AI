from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from app.models import ProjectStatus, TaskStatus

# --- Auth Schemas ---

class UserRegister(BaseModel):
    email: EmailStr = Field(..., description="Unique email address for user registration")
    password: str = Field(..., min_length=8, max_length=100, description="Password (min 8 characters)")

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

# --- Project Schemas ---

class ProjectBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=1000)
    status: ProjectStatus = Field(default=ProjectStatus.DRAFT)

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=1000)
    status: Optional[ProjectStatus] = None

class ProjectResponse(ProjectBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_id: UUID
    created_at: datetime
    updated_at: datetime

# --- Task Schemas ---

class TaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=1000)
    status: TaskStatus = Field(default=TaskStatus.TODO)
    priority: int = Field(default=0, ge=0, le=3, description="Priority rating (0=low, 3=critical)")
    order_index: int = Field(default=0, ge=0)
    due_date: Optional[datetime] = None

class TaskCreate(TaskBase):
    pass

class TaskUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=1000)
    status: Optional[TaskStatus] = None
    priority: Optional[int] = Field(default=None, ge=0, le=3)
    order_index: Optional[int] = Field(default=None, ge=0)
    due_date: Optional[datetime] = None

class TaskResponse(TaskBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    created_at: datetime
    updated_at: datetime


# --- AI Suggestion Schemas ---

class AIPriorityResponse(BaseModel):
    suggested_priority: int
    reasoning: str
    confidence: float  # 0.0-1.0


class AIDeadlineResponse(BaseModel):
    suggested_due_date: Optional[datetime] = None
    confidence: float = 0.5
    reasoning: str


class AIDescriptionResponse(BaseModel):
    description: str
    confidence: float


class AISuggestedTasksResponse(BaseModel):
    suggestions: list["AISuggestionItem"]


class AISuggestionItem(BaseModel):
    title: str
    description: Optional[str] = None
    priority: int = 0


class HealthTask(BaseModel):
    task: str
    status: str
    priority: int


class HealthScoreResponse(BaseModel):
    score: float
    progress_pct: float
    total: int
    completed: int
    overdue_count: int
    high_prio_open: int
    flag: Optional[str] = None
    recent_tasks: list[HealthTask]
    project_title: str = ""
