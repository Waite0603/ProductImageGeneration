import json
import os
import sqlite3
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

DEFAULT_DB = Path(__file__).resolve().parent.parent / "data" / "showcase.db"
DB_PATH = Path(os.environ.get("DATABASE_PATH", str(DEFAULT_DB)))


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS histories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


class HistoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    payload: dict


class HistoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    payload: dict | None = None


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Product Showcase History", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def escape_like(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}


@app.get("/api/histories")
def list_histories(
    q: str = "",
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> dict:
    keyword = q.strip()
    offset = (page - 1) * page_size
    where = ""
    params: list = []
    if keyword:
        where = "WHERE name LIKE ? ESCAPE '\\'"
        params.append(f"%{escape_like(keyword)}%")

    with get_conn() as conn:
        total = conn.execute(
            f"SELECT COUNT(*) AS n FROM histories {where}",
            params,
        ).fetchone()["n"]
        rows = conn.execute(
            f"""
            SELECT id, name, created_at
            FROM histories
            {where}
            ORDER BY id DESC
            LIMIT ? OFFSET ?
            """,
            [*params, page_size, offset],
        ).fetchall()

    items = [dict(row) for row in rows]
    return {
        "items": items,
        "total": int(total),
        "page": page,
        "page_size": page_size,
        "has_more": offset + len(items) < int(total),
    }


@app.post("/api/histories")
def create_history(body: HistoryCreate) -> dict:
    created_at = utc_now()
    payload = json.dumps(body.payload, ensure_ascii=False)
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO histories (name, payload, created_at) VALUES (?, ?, ?)",
            (body.name.strip(), payload, created_at),
        )
        history_id = cur.lastrowid
    return {"id": history_id, "name": body.name.strip(), "created_at": created_at}


@app.get("/api/histories/{history_id}")
def get_history(history_id: int) -> dict:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, name, payload, created_at FROM histories WHERE id = ?",
            (history_id,),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="记录不存在")
    data = dict(row)
    data["payload"] = json.loads(data["payload"])
    return data


@app.patch("/api/histories/{history_id}")
def update_history(history_id: int, body: HistoryUpdate) -> dict:
    if body.name is None and body.payload is None:
        raise HTTPException(status_code=400, detail="没有要更新的内容")

    sets = []
    values = []
    if body.name is not None:
        sets.append("name = ?")
        values.append(body.name.strip())
    if body.payload is not None:
        sets.append("payload = ?")
        values.append(json.dumps(body.payload, ensure_ascii=False))
    values.append(history_id)

    with get_conn() as conn:
        cur = conn.execute(
            f"UPDATE histories SET {', '.join(sets)} WHERE id = ?",
            values,
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="记录不存在")
        row = conn.execute(
            "SELECT id, name, created_at FROM histories WHERE id = ?",
            (history_id,),
        ).fetchone()
    return dict(row)


@app.delete("/api/histories/{history_id}")
def delete_history(history_id: int) -> dict:
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM histories WHERE id = ?", (history_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="记录不存在")
    return {"ok": True}
