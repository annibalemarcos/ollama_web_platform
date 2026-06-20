import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

DB_PATH = Path(__file__).resolve().parent / "data" / "history.db"


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                query TEXT NOT NULL,
                answer TEXT NOT NULL,
                model TEXT NOT NULL,
                max_results INTEGER NOT NULL DEFAULT 5,
                sources_json TEXT NOT NULL DEFAULT '[]'
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS usage_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                query TEXT NOT NULL DEFAULT '',
                model TEXT NOT NULL DEFAULT '',
                web_ok INTEGER NOT NULL DEFAULT 0,
                chat_ok INTEGER NOT NULL DEFAULT 0,
                source_count INTEGER NOT NULL DEFAULT 0,
                prompt_chars INTEGER NOT NULL DEFAULT 0,
                answer_chars INTEGER NOT NULL DEFAULT 0,
                prompt_eval_count INTEGER NOT NULL DEFAULT 0,
                eval_count INTEGER NOT NULL DEFAULT 0,
                total_duration_ns INTEGER NOT NULL DEFAULT 0,
                load_duration_ns INTEGER NOT NULL DEFAULT 0,
                prompt_eval_duration_ns INTEGER NOT NULL DEFAULT 0,
                eval_duration_ns INTEGER NOT NULL DEFAULT 0,
                error_message TEXT NOT NULL DEFAULT '',
                rate_headers_json TEXT NOT NULL DEFAULT '{}'
            )
            """
        )
        conn.commit()


def add_history(query: str, answer: str, model: str, max_results: int, sources: List[Dict[str, Any]]) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO history (query, answer, model, max_results, sources_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (query, answer, model, max_results, json.dumps(sources, ensure_ascii=False)),
        )
        conn.commit()
        return int(cur.lastrowid)


def add_usage_log(
    *,
    query: str,
    model: str,
    web_ok: bool,
    chat_ok: bool,
    source_count: int = 0,
    prompt_chars: int = 0,
    answer_chars: int = 0,
    metrics: Optional[Dict[str, Any]] = None,
    error_message: str = "",
    rate_headers: Optional[Dict[str, str]] = None,
) -> int:
    metrics = metrics or {}
    rate_headers = rate_headers or {}
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO usage_logs (
                query, model, web_ok, chat_ok, source_count, prompt_chars, answer_chars,
                prompt_eval_count, eval_count, total_duration_ns, load_duration_ns,
                prompt_eval_duration_ns, eval_duration_ns, error_message, rate_headers_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                query,
                model,
                1 if web_ok else 0,
                1 if chat_ok else 0,
                int(source_count or 0),
                int(prompt_chars or 0),
                int(answer_chars or 0),
                int(metrics.get("prompt_eval_count") or 0),
                int(metrics.get("eval_count") or 0),
                int(metrics.get("total_duration") or 0),
                int(metrics.get("load_duration") or 0),
                int(metrics.get("prompt_eval_duration") or 0),
                int(metrics.get("eval_duration") or 0),
                error_message[:1500],
                json.dumps(rate_headers, ensure_ascii=False),
            ),
        )
        conn.commit()
        return int(cur.lastrowid)


def list_history(limit: int = 100) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, created_at, query, answer, model, max_results, sources_json
            FROM history
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [_history_row_to_dict(row) for row in rows]


def get_history(item_id: int) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT id, created_at, query, answer, model, max_results, sources_json
            FROM history
            WHERE id = ?
            """,
            (item_id,),
        ).fetchone()
    return _history_row_to_dict(row) if row else None


def delete_history(item_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM history WHERE id = ?", (item_id,))
        conn.commit()


def clear_history() -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM history")
        conn.commit()


def usage_stats() -> Dict[str, Any]:
    windows = {
        "hour": "-1 hour",
        "day": "-1 day",
        "week": "-7 days",
        "month": "-30 days",
        "all": None,
    }
    stats = {}
    with get_connection() as conn:
        for key, modifier in windows.items():
            where = ""
            params: tuple[Any, ...] = ()
            if modifier:
                where = "WHERE created_at >= datetime('now', 'localtime', ?)"
                params = (modifier,)
            row = conn.execute(
                f"""
                SELECT
                    COUNT(*) AS total_requests,
                    SUM(CASE WHEN source_count > 0 THEN 1 ELSE 0 END) AS web_searches,
                    SUM(CASE WHEN chat_ok = 1 THEN 1 ELSE 0 END) AS successful_answers,
                    SUM(CASE WHEN COALESCE(error_message, '') != '' OR chat_ok = 0 THEN 1 ELSE 0 END) AS errors,
                    COALESCE(SUM(source_count), 0) AS sources_used,
                    COALESCE(SUM(prompt_eval_count), 0) AS input_tokens,
                    COALESCE(SUM(eval_count), 0) AS output_tokens,
                    COALESCE(SUM(total_duration_ns), 0) AS total_duration_ns,
                    COALESCE(AVG(NULLIF(total_duration_ns, 0)), 0) AS avg_duration_ns
                FROM usage_logs
                {where}
                """,
                params,
            ).fetchone()
            stats[key] = dict(row)

        last = conn.execute(
            """
            SELECT * FROM usage_logs
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()
    stats["last"] = _usage_row_to_dict(last) if last else None
    return stats


def recent_usage_logs(limit: int = 20) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM usage_logs ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [_usage_row_to_dict(row) for row in rows]


def _history_row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    data = dict(row)
    try:
        data["sources"] = json.loads(data.pop("sources_json") or "[]")
    except json.JSONDecodeError:
        data["sources"] = []
    return data


def _usage_row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    data = dict(row)
    try:
        data["rate_headers"] = json.loads(data.pop("rate_headers_json") or "{}")
    except json.JSONDecodeError:
        data["rate_headers"] = {}
    return data
