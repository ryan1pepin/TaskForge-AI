import uuid
import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models import Project, Task

async def get_auth_headers(client: AsyncClient, email: str) -> dict:
    """Helper to register a user and return authorization headers."""
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "securepassword123"}
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.mark.asyncio
async def test_project_crud_lifecycle(client: AsyncClient, db_session: AsyncSession):
    headers = await get_auth_headers(client, "project@example.com")

    # 1. Create Project
    response = await client.post(
        "/api/v1/projects",
        json={"title": "Test Project", "description": "A test workspace description"},
        headers=headers
    )
    assert response.status_code == status.HTTP_201_CREATED
    project_id = response.json()["id"]
    assert response.json()["title"] == "Test Project"
    assert response.json()["status"] == "draft"

    # 2. Get Project details
    get_res = await client.get(f"/api/v1/projects/{project_id}", headers=headers)
    assert get_res.status_code == status.HTTP_200_OK
    assert get_res.json()["title"] == "Test Project"

    # 3. List Projects
    list_res = await client.get("/api/v1/projects", headers=headers)
    assert list_res.status_code == status.HTTP_200_OK
    assert len(list_res.json()) == 1

    # 4. Update Project
    patch_res = await client.patch(
        f"/api/v1/projects/{project_id}",
        json={"title": "Updated Title", "status": "active"},
        headers=headers
    )
    assert patch_res.status_code == status.HTTP_200_OK
    assert patch_res.json()["title"] == "Updated Title"
    assert patch_res.json()["status"] == "active"

    # 5. Soft Delete Project
    del_res = await client.delete(f"/api/v1/projects/{project_id}", headers=headers)
    assert del_res.status_code == status.HTTP_204_NO_CONTENT

    # 6. Verify omitted from lists and detail returns 404
    list_after = await client.get("/api/v1/projects", headers=headers)
    assert len(list_after.json()) == 0

    get_after = await client.get(f"/api/v1/projects/{project_id}", headers=headers)
    assert get_after.status_code == status.HTTP_404_NOT_FOUND

    # 7. Check database row still exists (soft-deleted)
    # Cast to uuid.UUID — SQLite returns IDs as strings from JSON, but SQLAlchemy expects UUID objects
    result = await db_session.execute(select(Project).where(Project.id == uuid.UUID(project_id)))
    db_proj = result.scalars().first()
    assert db_proj is not None
    assert db_proj.deleted_at is not None

@pytest.mark.asyncio
async def test_project_pagination(client: AsyncClient):
    headers = await get_auth_headers(client, "pagination@example.com")
    
    # Create 5 projects
    for i in range(5):
        await client.post(
            "/api/v1/projects",
            json={"title": f"Proj {i}", "status": "active"},
            headers=headers
        )

    # Fetch offset 0 limit 2
    res1 = await client.get("/api/v1/projects?limit=2&offset=0", headers=headers)
    assert len(res1.json()) == 2
    assert res1.json()[0]["title"] == "Proj 0"

    # Fetch offset 2 limit 2
    res2 = await client.get("/api/v1/projects?limit=2&offset=2", headers=headers)
    assert len(res2.json()) == 2
    assert res2.json()[0]["title"] == "Proj 2"

@pytest.mark.asyncio
async def test_task_operations_and_cascade_soft_delete(client: AsyncClient, db_session: AsyncSession):
    headers = await get_auth_headers(client, "task@example.com")

    # Create a project
    p_res = await client.post(
        "/api/v1/projects",
        json={"title": "Task Holder"},
        headers=headers
    )
    pid = p_res.json()["id"]

    # 1. Create two tasks with different order indexes
    t1_res = await client.post(
        f"/api/v1/projects/{pid}/tasks",
        json={"title": "Second Task", "order_index": 2, "priority": 1},
        headers=headers
    )
    t2_res = await client.post(
        f"/api/v1/projects/{pid}/tasks",
        json={"title": "First Task", "order_index": 1, "priority": 3},
        headers=headers
    )
    assert t1_res.status_code == status.HTTP_201_CREATED
    tid1 = t1_res.json()["id"]
    tid2 = t2_res.json()["id"]

    # 2. Get tasks (verify sorted by order_index asc, so task 2 comes first)
    list_res = await client.get(f"/api/v1/projects/{pid}/tasks", headers=headers)
    assert list_res.status_code == status.HTTP_200_OK
    tasks = list_res.json()
    assert len(tasks) == 2
    assert tasks[0]["id"] == tid2  # order_index 1
    assert tasks[1]["id"] == tid1  # order_index 2

    # 3. Patch task details
    patch_res = await client.patch(
        f"/api/v1/projects/{pid}/tasks/{tid2}",
        json={"status": "in_progress", "priority": 2},
        headers=headers
    )
    assert patch_res.status_code == status.HTTP_200_OK
    assert patch_res.json()["status"] == "in_progress"
    assert patch_res.json()["priority"] == 2

    # 4. Soft delete task 1
    del_res = await client.delete(f"/api/v1/projects/{pid}/tasks/{tid1}", headers=headers)
    assert del_res.status_code == status.HTTP_204_NO_CONTENT

    # List tasks again, only task 2 should remain
    list_res2 = await client.get(f"/api/v1/projects/{pid}/tasks", headers=headers)
    assert len(list_res2.json()) == 1
    assert list_res2.json()[0]["id"] == tid2

    # 5. Delete project (verifies cascade soft deletion)
    await client.delete(f"/api/v1/projects/{pid}", headers=headers)

    # Verify both task rows still exist in database but are flagged as soft-deleted
    # Cast string IDs from JSON response to uuid.UUID for SQLAlchemy compatibility with SQLite
    result = await db_session.execute(
        select(Task).where(Task.id.in_([uuid.UUID(tid1), uuid.UUID(tid2)]))
    )
    db_tasks = result.scalars().all()
    assert len(db_tasks) == 2
    for t in db_tasks:
        assert t.deleted_at is not None
