from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional
from server.schemas.content import _Permissive
from server.db import taskboard_repo

router = APIRouter(prefix="/taskboard", tags=["taskboard"])


class TaskboardUserCreate(_Permissive):
    name: str = Field(min_length=1, max_length=64)


class TaskboardUserUpdate(_Permissive):
    name: Optional[str] = Field(default=None, min_length=1, max_length=64)
    position: Optional[int] = Field(default=None, ge=0)


class TaskboardUserOut(_Permissive):
    id: int
    name: str
    position: int
    task_count: int
    created_at: str


class TaskboardTaskCreate(_Permissive):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)


class TaskboardTaskUpdate(_Permissive):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    assignee_id: Optional[int] = None
    position: Optional[int] = Field(default=None, ge=0)


class TaskboardTaskOut(_Permissive):
    id: int
    title: str
    description: str
    assignee_id: Optional[int]
    position: int
    status: str
    created_at: str
    updated_at: str


@router.get("/users")
async def get_users():
    return await taskboard_repo.list_users()


@router.post("/users")
async def post_user(body: TaskboardUserCreate):
    return await taskboard_repo.create_user(body.name)


@router.patch("/users/{user_id}")
async def patch_user(user_id: int, req: TaskboardUserUpdate):
    patch = req.model_dump(exclude_unset=True)
    user = await taskboard_repo.update_user(user_id, **patch)
    if user is None:
        raise HTTPException(
            status_code=404, detail={"error": "Not found", "code": "NOT_FOUND"}
        )
    return user


@router.delete("/users/{user_id}")
async def delete_user(user_id: int):
    await taskboard_repo.archive_user(user_id)
    return {"ok": True}


@router.get("/tasks")
async def get_tasks(assignee_id: Optional[str] = Query(default=None)):
    if assignee_id is None:
        tasks = await taskboard_repo.list_tasks(taskboard_repo.NULL_SENTINEL)
    elif assignee_id == "null":
        tasks = await taskboard_repo.list_tasks(None)
    else:
        try:
            parsed_id = int(assignee_id)
        except ValueError:
            raise HTTPException(
                status_code=422,
                detail={"error": "Invalid assignee_id", "code": "INVALID_PARAMETER"},
            )
        tasks = await taskboard_repo.list_tasks(parsed_id)
    return tasks


@router.post("/tasks")
async def post_task(body: TaskboardTaskCreate):
    return await taskboard_repo.create_task(body.title, body.description)


@router.patch("/tasks/{task_id}")
async def patch_task(task_id: int, req: TaskboardTaskUpdate):
    patch = req.model_dump(exclude_unset=True)
    task = await taskboard_repo.update_task(task_id, **patch)
    if task is None:
        raise HTTPException(
            status_code=404, detail={"error": "Not found", "code": "NOT_FOUND"}
        )
    return task


@router.delete("/tasks/{task_id}")
async def delete_task(task_id: int):
    await taskboard_repo.archive_task(task_id)
    return {"ok": True}
