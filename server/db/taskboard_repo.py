from typing import Optional

from .connection import connect, _now

NULL_SENTINEL = object()


# --------------------------------------------------------------------------- #
# Users
# --------------------------------------------------------------------------- #

async def list_users() -> list[dict]:
    db = await connect()
    try:
        cursor = await db.execute(
            """
            SELECT
                u.id,
                u.name,
                u.position,
                u.color,
                u.created_at,
                COUNT(t.id) AS task_count
            FROM taskboard_users u
            LEFT JOIN taskboard_tasks t
                ON t.assignee_id = u.id AND t.archived_at IS NULL
            WHERE u.archived_at IS NULL
            GROUP BY u.id
            ORDER BY u.position ASC, u.id ASC
            """
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()


async def create_user(name, color=None) -> dict:
    db = await connect()
    try:
        cursor = await db.execute(
            "SELECT MAX(position) FROM taskboard_users WHERE archived_at IS NULL"
        )
        row = await cursor.fetchone()
        position = (row[0] + 1) if row[0] is not None else 0

        cursor = await db.execute(
            "INSERT INTO taskboard_users (name, position, color, created_at) VALUES (?, ?, ?, ?)",
            (name, position, color, _now()),
        )
        user_id = cursor.lastrowid
        await db.commit()

        cursor = await db.execute(
            """
            SELECT
                u.id,
                u.name,
                u.position,
                u.color,
                u.created_at,
                COUNT(t.id) AS task_count
            FROM taskboard_users u
            LEFT JOIN taskboard_tasks t
                ON t.assignee_id = u.id AND t.archived_at IS NULL
            WHERE u.id = ?
            GROUP BY u.id
            """,
            (user_id,),
        )
        row = await cursor.fetchone()
        return dict(row)
    finally:
        await db.close()


async def update_user(user_id, *, name=None, position=None, color=None) -> Optional[dict]:
    db = await connect()
    try:
        cursor = await db.execute(
            "SELECT id, position FROM taskboard_users WHERE id = ? AND archived_at IS NULL",
            (user_id,),
        )
        row = await cursor.fetchone()
        if not row:
            return None

        if name is not None:
            await db.execute(
                "UPDATE taskboard_users SET name = ? WHERE id = ?",
                (name, user_id),
            )
            await db.commit()

        if color is not None:
            await db.execute(
                "UPDATE taskboard_users SET color = ? WHERE id = ?",
                (color, user_id),
            )
            await db.commit()

        if position is not None:
            current_pos = row["position"]
            if position < current_pos:
                await db.execute(
                    "UPDATE taskboard_users SET position = position + 1 WHERE archived_at IS NULL AND position >= ? AND position < ?",
                    (position, current_pos),
                )
            elif position > current_pos:
                await db.execute(
                    "UPDATE taskboard_users SET position = position - 1 WHERE archived_at IS NULL AND position > ? AND position <= ?",
                    (current_pos, position),
                )
            await db.execute(
                "UPDATE taskboard_users SET position = ? WHERE id = ?",
                (position, user_id),
            )
            await db.commit()

        cursor = await db.execute(
            """
            SELECT
                u.id,
                u.name,
                u.position,
                u.color,
                u.created_at,
                COUNT(t.id) AS task_count
            FROM taskboard_users u
            LEFT JOIN taskboard_tasks t
                ON t.assignee_id = u.id AND t.archived_at IS NULL
            WHERE u.id = ?
            GROUP BY u.id
            """,
            (user_id,),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await db.close()


async def archive_user(user_id) -> None:
    db = await connect()
    try:
        await db.execute(
            "UPDATE taskboard_users SET archived_at = ? WHERE id = ? AND archived_at IS NULL",
            (_now(), user_id),
        )
        await db.execute(
            "UPDATE taskboard_tasks SET assignee_id = NULL WHERE assignee_id = ?",
            (user_id,),
        )
        await db.commit()
    finally:
        await db.close()


# --------------------------------------------------------------------------- #
# Tasks
# --------------------------------------------------------------------------- #

async def list_tasks(assignee_id=NULL_SENTINEL) -> list[dict]:
    db = await connect()
    try:
        if assignee_id is NULL_SENTINEL:
            cursor = await db.execute(
                """
                SELECT id, title, description, assignee_id, position, status,
                       task_type, subtask_total, subtask_done, attachment_count, cover_url,
                       created_at, updated_at
                FROM taskboard_tasks
                WHERE archived_at IS NULL
                ORDER BY position ASC, id ASC
                """
            )
        elif assignee_id is None:
            cursor = await db.execute(
                """
                SELECT id, title, description, assignee_id, position, status,
                       task_type, subtask_total, subtask_done, attachment_count, cover_url,
                       created_at, updated_at
                FROM taskboard_tasks
                WHERE archived_at IS NULL AND assignee_id IS NULL
                ORDER BY position ASC, id ASC
                """
            )
        else:
            cursor = await db.execute(
                """
                SELECT id, title, description, assignee_id, position, status,
                       task_type, subtask_total, subtask_done, attachment_count, cover_url,
                       created_at, updated_at
                FROM taskboard_tasks
                WHERE archived_at IS NULL AND assignee_id = ?
                ORDER BY position ASC, id ASC
                """,
                (assignee_id,),
            )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()


async def create_task(
    title,
    description="",
    *,
    task_type="general",
    subtask_total=0,
    subtask_done=0,
    attachment_count=0,
    cover_url=None,
    assignee_id=None,
) -> dict:
    db = await connect()
    try:
        if assignee_id is None:
            cursor = await db.execute(
                "SELECT MAX(position) FROM taskboard_tasks WHERE archived_at IS NULL AND assignee_id IS NULL"
            )
        else:
            cursor = await db.execute(
                "SELECT MAX(position) FROM taskboard_tasks WHERE archived_at IS NULL AND assignee_id = ?",
                (assignee_id,),
            )
        row = await cursor.fetchone()
        position = (row[0] + 1) if row[0] is not None else 0

        now = _now()
        cursor = await db.execute(
            """
            INSERT INTO taskboard_tasks (
              title, description, assignee_id, position, status,
              task_type, subtask_total, subtask_done, attachment_count, cover_url,
              created_at, updated_at
            )
            VALUES (?, ?, ?, ?, 'open', ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                title,
                description,
                assignee_id,
                position,
                task_type,
                subtask_total,
                subtask_done,
                attachment_count,
                cover_url,
                now,
                now,
            ),
        )
        task_id = cursor.lastrowid
        await db.commit()

        cursor = await db.execute(
            """
            SELECT id, title, description, assignee_id, position, status,
                       task_type, subtask_total, subtask_done, attachment_count, cover_url,
                       created_at, updated_at
            FROM taskboard_tasks
            WHERE id = ?
            """,
            (task_id,),
        )
        row = await cursor.fetchone()
        return dict(row)
    finally:
        await db.close()


async def _repack_bucket(db, assignee_id) -> None:
    if assignee_id is None:
        cursor = await db.execute(
            """
            SELECT id FROM taskboard_tasks
            WHERE archived_at IS NULL AND assignee_id IS NULL
            ORDER BY position ASC, id ASC
            """
        )
    else:
        cursor = await db.execute(
            """
            SELECT id FROM taskboard_tasks
            WHERE archived_at IS NULL AND assignee_id = ?
            ORDER BY position ASC, id ASC
            """,
            (assignee_id,),
        )
    rows = await cursor.fetchall()
    for new_pos, row in enumerate(rows):
        await db.execute(
            "UPDATE taskboard_tasks SET position = ? WHERE id = ?",
            (new_pos, row["id"]),
        )


async def update_task(task_id, **patch) -> Optional[dict]:
    db = await connect()
    try:
        cursor = await db.execute(
            "SELECT * FROM taskboard_tasks WHERE id = ? AND archived_at IS NULL",
            (task_id,),
        )
        current = await cursor.fetchone()
        if not current:
            return None

        current = dict(current)
        old_assignee = current.get("assignee_id")
        new_assignee = patch.get("assignee_id") if "assignee_id" in patch else old_assignee

        # Handle within-bucket reorder (no assignee change, position provided)
        if "position" in patch and old_assignee == new_assignee:
            target_pos = patch["position"]
            current_pos = current["position"]
            if target_pos < current_pos:
                if old_assignee is None:
                    await db.execute(
                        "UPDATE taskboard_tasks SET position = position + 1 WHERE archived_at IS NULL AND assignee_id IS NULL AND position >= ? AND position < ?",
                        (target_pos, current_pos),
                    )
                else:
                    await db.execute(
                        "UPDATE taskboard_tasks SET position = position + 1 WHERE archived_at IS NULL AND assignee_id = ? AND position >= ? AND position < ?",
                        (old_assignee, target_pos, current_pos),
                    )
            elif target_pos > current_pos:
                if old_assignee is None:
                    await db.execute(
                        "UPDATE taskboard_tasks SET position = position - 1 WHERE archived_at IS NULL AND assignee_id IS NULL AND position > ? AND position <= ?",
                        (current_pos, target_pos),
                    )
                else:
                    await db.execute(
                        "UPDATE taskboard_tasks SET position = position - 1 WHERE archived_at IS NULL AND assignee_id = ? AND position > ? AND position <= ?",
                        (old_assignee, current_pos, target_pos),
                    )
            await db.execute(
                "UPDATE taskboard_tasks SET position = ?, updated_at = ? WHERE id = ?",
                (target_pos, _now(), task_id),
            )
            await db.commit()
        else:
            # Standard update (title, description, assignee_id, or cross-bucket with position)
            fields = []
            values = []
            if "title" in patch:
                fields.append("title = ?")
                values.append(patch["title"])
            if "description" in patch:
                fields.append("description = ?")
                values.append(patch["description"])
            if "assignee_id" in patch:
                fields.append("assignee_id = ?")
                values.append(patch["assignee_id"])
            if "position" in patch:
                fields.append("position = ?")
                values.append(patch["position"])
            if "status" in patch:
                fields.append("status = ?")
                values.append(patch["status"])
            if "task_type" in patch:
                fields.append("task_type = ?")
                values.append(patch["task_type"])
            if "subtask_total" in patch:
                fields.append("subtask_total = ?")
                values.append(patch["subtask_total"])
            if "subtask_done" in patch:
                fields.append("subtask_done = ?")
                values.append(patch["subtask_done"])
            if "attachment_count" in patch:
                fields.append("attachment_count = ?")
                values.append(patch["attachment_count"])
            if "cover_url" in patch:
                fields.append("cover_url = ?")
                values.append(patch["cover_url"])

            if fields:
                fields.append("updated_at = ?")
                values.append(_now())
                values.append(task_id)
                await db.execute(
                    f"UPDATE taskboard_tasks SET {', '.join(fields)} WHERE id = ?",
                    values,
                )
                await db.commit()

            if "assignee_id" in patch and new_assignee != old_assignee:
                await _repack_bucket(db, old_assignee)
                await _repack_bucket(db, new_assignee)
                await db.commit()

        cursor = await db.execute(
            """
            SELECT id, title, description, assignee_id, position, status,
                       task_type, subtask_total, subtask_done, attachment_count, cover_url,
                       created_at, updated_at
            FROM taskboard_tasks
            WHERE id = ?
            """,
            (task_id,),
        )
        row = await cursor.fetchone()
        return dict(row)
    finally:
        await db.close()


async def archive_task(task_id) -> None:
    db = await connect()
    try:
        cursor = await db.execute(
            "SELECT assignee_id FROM taskboard_tasks WHERE id = ? AND archived_at IS NULL",
            (task_id,),
        )
        row = await cursor.fetchone()
        if not row:
            return

        assignee_id = row["assignee_id"]

        await db.execute(
            "UPDATE taskboard_tasks SET archived_at = ? WHERE id = ?",
            (_now(), task_id),
        )
        await db.commit()

        await _repack_bucket(db, assignee_id)
        await db.commit()
    finally:
        await db.close()
