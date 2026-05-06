from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from typing import Literal, Optional
from server.schemas.content import _Permissive
from server.db import taskboard_repo

router = APIRouter(prefix="/taskboard", tags=["taskboard"])

# Allowed semantic task types — keep narrow so the column accent palette
# stays in lockstep with the backend. Add to both this list and the CSS
# palette in frontend/css/taskboard.css when introducing new ones.
TASK_TYPES = ("general", "development", "design", "research", "ops")
USER_COLOR_PATTERN = r"^#[0-9a-fA-F]{6}$"


class TaskboardUserCreate(_Permissive):
    name: str = Field(min_length=1, max_length=64)
    color: Optional[str] = Field(default=None, pattern=USER_COLOR_PATTERN)


class TaskboardUserUpdate(_Permissive):
    name: Optional[str] = Field(default=None, min_length=1, max_length=64)
    position: Optional[int] = Field(default=None, ge=0)
    color: Optional[str] = Field(default=None, pattern=USER_COLOR_PATTERN)


class TaskboardUserOut(_Permissive):
    id: int
    name: str
    position: int
    color: Optional[str]
    task_count: int
    created_at: str


class TaskboardTaskCreate(_Permissive):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)
    task_type: Optional[str] = Field(default=None, max_length=32)
    assignee_id: Optional[int] = None
    cover_url: Optional[str] = Field(default=None, max_length=500)
    subtask_total: Optional[int] = Field(default=None, ge=0, le=999)
    subtask_done: Optional[int] = Field(default=None, ge=0, le=999)
    attachment_count: Optional[int] = Field(default=None, ge=0, le=999)

    @field_validator("task_type")
    @classmethod
    def _validate_task_type(cls, v):
        if v is not None and v not in TASK_TYPES:
            raise ValueError(f"task_type must be one of {TASK_TYPES}")
        return v


class TaskboardTaskUpdate(_Permissive):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    assignee_id: Optional[int] = None
    position: Optional[int] = Field(default=None, ge=0)
    status: Optional[Literal["open", "done"]] = None
    task_type: Optional[str] = Field(default=None, max_length=32)
    subtask_total: Optional[int] = Field(default=None, ge=0, le=999)
    subtask_done: Optional[int] = Field(default=None, ge=0, le=999)
    attachment_count: Optional[int] = Field(default=None, ge=0, le=999)
    cover_url: Optional[str] = Field(default=None, max_length=500)

    @field_validator("task_type")
    @classmethod
    def _validate_task_type(cls, v):
        if v is not None and v not in TASK_TYPES:
            raise ValueError(f"task_type must be one of {TASK_TYPES}")
        return v


class TaskboardTaskOut(_Permissive):
    id: int
    title: str
    description: str
    assignee_id: Optional[int]
    position: int
    status: str
    task_type: str
    subtask_total: int
    subtask_done: int
    attachment_count: int
    cover_url: Optional[str]
    created_at: str
    updated_at: str


@router.get("/users")
async def get_users():
    return await taskboard_repo.list_users()


@router.post("/users")
async def post_user(body: TaskboardUserCreate):
    return await taskboard_repo.create_user(body.name, color=body.color)


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
    kwargs = {}
    if body.task_type is not None:
        kwargs["task_type"] = body.task_type
    if body.assignee_id is not None:
        kwargs["assignee_id"] = body.assignee_id
    if body.cover_url is not None:
        kwargs["cover_url"] = body.cover_url
    if body.subtask_total is not None:
        kwargs["subtask_total"] = body.subtask_total
    if body.subtask_done is not None:
        kwargs["subtask_done"] = body.subtask_done
    if body.attachment_count is not None:
        kwargs["attachment_count"] = body.attachment_count
    return await taskboard_repo.create_task(body.title, body.description, **kwargs)


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
