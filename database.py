import sqlite3
import logging
from contextlib import contextmanager
from datetime import datetime
from config import DB_PATH

logger = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS seen_jobs (
    job_id      TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    company     TEXT NOT NULL,
    url         TEXT NOT NULL,
    is_matched  INTEGER NOT NULL DEFAULT 0,   -- 1: AI가 조건 부합 판정
    notified    INTEGER NOT NULL DEFAULT 0,   -- 1: 슬랙 알림 발송 완료
    created_at  TEXT NOT NULL
);
"""


@contextmanager
def _conn():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def init_db() -> None:
    with _conn() as con:
        con.executescript(SCHEMA)
    logger.info("DB 초기화 완료: %s", DB_PATH)


def is_seen(job_id: str) -> bool:
    """이미 처리한 공고인지 확인한다."""
    with _conn() as con:
        row = con.execute(
            "SELECT 1 FROM seen_jobs WHERE job_id = ?", (job_id,)
        ).fetchone()
    return row is not None


def mark_seen(job_id: str, title: str, company: str, url: str, is_matched: bool = False) -> None:
    """공고를 처리 완료로 기록한다."""
    with _conn() as con:
        con.execute(
            """
            INSERT OR IGNORE INTO seen_jobs (job_id, title, company, url, is_matched, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (job_id, title, company, url, int(is_matched), datetime.now().isoformat()),
        )


def mark_notified(job_id: str) -> None:
    """슬랙 알림 발송 완료로 기록한다."""
    with _conn() as con:
        con.execute(
            "UPDATE seen_jobs SET notified = 1 WHERE job_id = ?", (job_id,)
        )


def get_stats() -> dict:
    """DB 통계를 반환한다."""
    with _conn() as con:
        total = con.execute("SELECT COUNT(*) FROM seen_jobs").fetchone()[0]
        matched = con.execute("SELECT COUNT(*) FROM seen_jobs WHERE is_matched = 1").fetchone()[0]
        notified = con.execute("SELECT COUNT(*) FROM seen_jobs WHERE notified = 1").fetchone()[0]
    return {"total": total, "matched": matched, "notified": notified}
