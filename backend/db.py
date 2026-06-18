import json
import os
from contextlib import contextmanager
from typing import Any

import psycopg2
from psycopg2.extras import Json, RealDictCursor


class DatabaseError(Exception):
    pass


def _get_database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise DatabaseError(
            "DATABASE_URL is not set. Add it to your .env file."
        )
    return url


@contextmanager
def get_connection():
    conn = psycopg2.connect(_get_database_url())
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS analyses (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id),
                    resource_group VARCHAR(255) NOT NULL,
                    resources_scanned INTEGER DEFAULT 0,
                    issues_found INTEGER DEFAULT 0,
                    estimated_savings TEXT,
                    analysis_result JSONB,
                    status VARCHAR(50) NOT NULL DEFAULT 'in_progress',
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
                """
            )


def get_user_by_email(email: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT id, email, password_hash, created_at FROM users WHERE email = %s",
                (email.lower(),),
            )
            row = cur.fetchone()
            return dict(row) if row else None


def create_user(email: str, password_hash: str) -> dict[str, Any]:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO users (email, password_hash)
                VALUES (%s, %s)
                RETURNING id, email, created_at
                """,
                (email.lower(), password_hash),
            )
            row = cur.fetchone()
            if row is None:
                raise DatabaseError("Failed to create user.")
            return dict(row)


def create_analysis(
    resource_group: str, user_id: int | None = None
) -> int:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO analyses (user_id, resource_group, status)
                VALUES (%s, %s, 'in_progress')
                RETURNING id
                """,
                (user_id, resource_group),
            )
            row = cur.fetchone()
            if row is None:
                raise DatabaseError("Failed to create analysis record.")
            return row[0]


def complete_analysis(
    analysis_id: int,
    *,
    resources_scanned: int,
    issues_found: int,
    estimated_savings: str,
    analysis_result: dict[str, Any],
) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE analyses
                SET resources_scanned = %s,
                    issues_found = %s,
                    estimated_savings = %s,
                    analysis_result = %s,
                    status = 'complete'
                WHERE id = %s
                """,
                (
                    resources_scanned,
                    issues_found,
                    estimated_savings,
                    Json(analysis_result),
                    analysis_id,
                ),
            )


def fail_analysis(
    analysis_id: int, error_message: str
) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE analyses
                SET status = 'failed',
                    analysis_result = %s
                WHERE id = %s
                """,
                (Json({"error": error_message}), analysis_id),
            )


def get_analysis_for_user(
    analysis_id: int, user_id: int
) -> dict[str, Any] | None:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT * FROM analyses
                WHERE id = %s AND user_id = %s
                """,
                (analysis_id, user_id),
            )
            row = cur.fetchone()
            return dict(row) if row else None


def get_analysis(analysis_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM analyses WHERE id = %s",
                (analysis_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None


def get_user_history(user_id: int) -> list[dict[str, Any]]:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, user_id, resource_group, resources_scanned,
                       issues_found, estimated_savings, analysis_result,
                       status, created_at
                FROM analyses
                WHERE user_id = %s
                ORDER BY created_at DESC
                """,
                (user_id,),
            )
            return [dict(row) for row in cur.fetchall()]


def serialize_analysis(row: dict[str, Any]) -> dict[str, Any]:
    serialized = dict(row)
    created_at = serialized.get("created_at")
    if created_at is not None:
        serialized["created_at"] = created_at.isoformat()
    result = serialized.get("analysis_result")
    if isinstance(result, str):
        serialized["analysis_result"] = json.loads(result)
    return serialized
