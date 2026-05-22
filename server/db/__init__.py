"""Re-export the legacy `server.db` flat module surface. Callers should still
do `from server.db import connect, get_homework, ...` and things should keep working.

The actual implementations live in the sub-modules."""

# connection layer
from .connection import (
    connect,
    checkpoint,
    apply_pragmas,
    _now,
    _today_stamp,
    _DURABILITY_PRAGMAS,
    _SNAPSHOT_MIN_INTERVAL_SEC,
    _SNAPSHOT_SIZE_DELTA_BYTES,
)

# get_db_path must be importable as `from server.db import get_db_path`
# AND patchable as `server.db.get_db_path` — re-export it here so patching
# `server.db.get_db_path` affects calls inside connection.py via the config module.
from ..config import get_db_path

# migrations
from .migrations import (
    init_db,
    _SCHEMA,
)

# homework CRUD
from .homework_repo import (
    list_homeworks,
    search_homeworks,
    list_trashed_homeworks,
    get_homework,
    create_homework,
    update_homework,
    delete_homework,
    hard_delete_homework,
    restore_homework,
    list_versions,
    get_version,
    restore_version,
    set_status,
    _row_to_homework,
    _next_id,
    _get_latest_version,
    _should_snapshot,
)

# review queue + answer cache
from .review_queue_repo import (
    get_answer_cache,
    set_answer_cache,
    add_to_review_queue,
    add_integrity_flag,
    get_review_queue,
    get_review_item_kind,
    resolve_review_item,
)

# authorship affirmations (academic-integrity §9.6)
from .affirmations_repo import (
    create_affirmation,
    list_affirmations,
)

# tutor conversations + warnings
from .tutor_repo import (
    add_tutor_turn,
    list_tutor_turns,
    count_session_messages,
    build_session_profile,
    add_warning,
    count_warnings_for_hw,
    count_warnings_for_session,
    list_recent_warnings,
    sum_deductions,
    summary_for_tutor,
)

# notebook captures
from .notebook_repo import (
    add_capture,
    get_capture,
    list_captures_for_session,
    count_captures_for_question,
    latest_capture,
)

# taskboard
from .taskboard_repo import (
    list_users as list_taskboard_users,
    create_user as create_taskboard_user,
    update_user as update_taskboard_user,
    archive_user as archive_taskboard_user,
    list_tasks as list_taskboard_tasks,
    create_task as create_taskboard_task,
    update_task as update_taskboard_task,
    archive_task as archive_taskboard_task,
    NULL_SENTINEL,
)

__all__ = [
    # connection
    "connect",
    "checkpoint",
    "apply_pragmas",
    "get_db_path",
    "_now",
    "_today_stamp",
    "_DURABILITY_PRAGMAS",
    "_SNAPSHOT_MIN_INTERVAL_SEC",
    "_SNAPSHOT_SIZE_DELTA_BYTES",
    # migrations
    "init_db",
    "_SCHEMA",
    # homework CRUD
    "list_homeworks",
    "search_homeworks",
    "list_trashed_homeworks",
    "get_homework",
    "create_homework",
    "update_homework",
    "delete_homework",
    "hard_delete_homework",
    "restore_homework",
    "list_versions",
    "get_version",
    "restore_version",
    "set_status",
    "_row_to_homework",
    "_next_id",
    "_get_latest_version",
    "_should_snapshot",
    # review queue + answer cache
    "get_answer_cache",
    "set_answer_cache",
    "add_to_review_queue",
    "add_integrity_flag",
    "get_review_queue",
    "get_review_item_kind",
    "resolve_review_item",
    # authorship affirmations
    "create_affirmation",
    "list_affirmations",
    # tutor
    "add_tutor_turn",
    "list_tutor_turns",
    "count_session_messages",
    "build_session_profile",
    "add_warning",
    "count_warnings_for_hw",
    "count_warnings_for_session",
    "list_recent_warnings",
    "sum_deductions",
    "summary_for_tutor",
    # notebook
    "add_capture",
    "get_capture",
    "list_captures_for_session",
    "count_captures_for_question",
    "latest_capture",
    # taskboard
    "list_taskboard_users",
    "create_taskboard_user",
    "update_taskboard_user",
    "archive_taskboard_user",
    "list_taskboard_tasks",
    "create_taskboard_task",
    "update_taskboard_task",
    "archive_taskboard_task",
    "NULL_SENTINEL",
]
