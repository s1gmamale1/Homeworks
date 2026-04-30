import json
from typing import Optional

from .connection import connect, _now


async def get_answer_cache(key: str) -> Optional[dict]:
    db = await connect()
    try:
        cursor = await db.execute(
            "SELECT response_json FROM answer_cache WHERE key = ?", (key,)
        )
        row = await cursor.fetchone()
        if row:
            return json.loads(row["response_json"])
        return None
    finally:
        await db.close()

async def set_answer_cache(key: str, response: dict) -> None:
    db = await connect()
    try:
        await db.execute(
            "INSERT OR REPLACE INTO answer_cache (key, response_json, created_at) VALUES (?, ?, ?)",
            (key, json.dumps(response, ensure_ascii=False), _now())
        )
        await db.commit()
    finally:
        await db.close()

async def add_to_review_queue(
    question_id: str,
    student_answer: str,
    answer_spec: dict,
    ai_response: dict,
) -> bool:
    """Insert a pending review item.  Idempotent: if a row with the same
    ``question_id`` + ``student_answer`` already has ``status='pending'``,
    the insert is skipped and ``False`` is returned.  Returns ``True`` when a
    new row was actually inserted.
    """
    db = await connect()
    try:
        # Dedup check: skip insert when an identical pending row already exists.
        cursor = await db.execute(
            "SELECT id FROM review_queue "
            "WHERE question_id = ? AND student_answer = ? AND status = 'pending' "
            "LIMIT 1",
            (question_id, student_answer),
        )
        existing = await cursor.fetchone()
        if existing:
            return False
        await db.execute(
            "INSERT INTO review_queue "
            "(question_id, student_answer, answer_spec_json, ai_response_json, status, created_at) "
            "VALUES (?, ?, ?, ?, 'pending', ?)",
            (
                question_id,
                student_answer,
                json.dumps(answer_spec, ensure_ascii=False),
                json.dumps(ai_response, ensure_ascii=False),
                _now(),
            ),
        )
        await db.commit()
        return True
    finally:
        await db.close()

async def get_review_queue() -> list[dict]:
    db = await connect()
    try:
        cursor = await db.execute(
            "SELECT * FROM review_queue WHERE status = 'pending' ORDER BY created_at ASC"
        )
        rows = await cursor.fetchall()
        res = []
        for r in rows:
            d = dict(r)
            d["answer_spec"] = json.loads(d.pop("answer_spec_json"))
            d["ai_response"] = json.loads(d.pop("ai_response_json"))
            res.append(d)
        return res
    finally:
        await db.close()

async def resolve_review_item(id: int, decision: dict) -> bool:
    """Persist the teacher's decision and mark the review item resolved.

    `decision` is stored verbatim as JSON so the schema doesn't need to grow
    every time we add a new field (e.g. {correct, score, feedback, override_reason}).
    """
    db = await connect()
    try:
        cursor = await db.execute(
            "UPDATE review_queue "
            "SET status = 'resolved', decision_json = ?, resolved_at = ? "
            "WHERE id = ? AND status = 'pending'",
            (json.dumps(decision, ensure_ascii=False), _now(), id),
        )
        await db.commit()
        return cursor.rowcount > 0
    finally:
        await db.close()
