import sys
import aiosqlite

from ..config import get_db_path
from datetime import datetime, timezone


# Pragmas that are per-connection and must be set every time a connection opens.
# WAL/synchronous are persistent on the DB file itself but are cheap to re-assert.
# foreign_keys and busy_timeout are strictly per-connection.
_DURABILITY_PRAGMAS = (
    "PRAGMA journal_mode = WAL;",
    "PRAGMA synchronous = FULL;",
    "PRAGMA foreign_keys = ON;",
    "PRAGMA busy_timeout = 5000;",
    "PRAGMA wal_autocheckpoint = 100;",
)

# Snapshot thresholds
_SNAPSHOT_MIN_INTERVAL_SEC = 120
_SNAPSHOT_SIZE_DELTA_BYTES = 500


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _today_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d")


async def apply_pragmas(db: aiosqlite.Connection) -> None:
    for stmt in _DURABILITY_PRAGMAS:
        await db.execute(stmt)


def _resolve_db_path():
    """Resolve the DB path, honouring any patch applied to server.db.get_db_path.

    Tests patch ``server.db.get_db_path`` to redirect to a temp DB.  Because
    ``connect()`` lives in ``server.db.connection``, calling the module-level
    ``get_db_path`` directly would bypass that patch.  Instead we look up the
    live ``server.db`` package object from ``sys.modules`` and call whatever
    ``get_db_path`` attribute is currently bound there (real or mocked).
    Falls back to the locally-imported function if the package isn't loaded yet.
    """
    pkg = sys.modules.get("server.db")
    if pkg is not None and hasattr(pkg, "get_db_path"):
        return pkg.get_db_path()
    return get_db_path()


async def connect() -> aiosqlite.Connection:
    db_path = _resolve_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db = await aiosqlite.connect(db_path)
    db.row_factory = aiosqlite.Row
    await apply_pragmas(db)
    return db


async def checkpoint() -> None:
    """Force a full WAL checkpoint. Call on graceful shutdown or periodically."""
    db_path = _resolve_db_path()
    async with aiosqlite.connect(db_path) as db:
        await apply_pragmas(db)
        await db.execute("PRAGMA wal_checkpoint(FULL)")
        await db.commit()
