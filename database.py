import json
import sqlite3
import logging
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime
from config import DB_PATH
from crawler import JobPosting

logger = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS seen_jobs (
    job_id      TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    company     TEXT NOT NULL,
    url         TEXT NOT NULL,
    is_matched  INTEGER NOT NULL DEFAULT 0,   -- 1: AI가 조건 부합 판정
    notified    INTEGER NOT NULL DEFAULT 0,   -- 1: 슬랙 알림 발송 완료
    filtered    INTEGER NOT NULL DEFAULT 0,   -- 1: AI 필터 처리 완료
    data_json   TEXT,                         -- JobPosting 직렬화 (필터 대기용)
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


def _migrate(con: sqlite3.Connection) -> None:
    """기존 DB에 누락된 컬럼을 추가한다. 기존 행은 이미 필터 완료 상태로 간주."""
    cols = {r[1] for r in con.execute("PRAGMA table_info(seen_jobs)")}
    if "filtered" not in cols:
        con.execute("ALTER TABLE seen_jobs ADD COLUMN filtered INTEGER NOT NULL DEFAULT 0")
        con.execute("UPDATE seen_jobs SET filtered = 1")  # 기존 행은 구 파이프라인에서 이미 판정됨
    if "data_json" not in cols:
        con.execute("ALTER TABLE seen_jobs ADD COLUMN data_json TEXT")


def init_db() -> None:
    with _conn() as con:
        con.executescript(SCHEMA)
        _migrate(con)
    logger.info("DB 초기화 완료: %s", DB_PATH)


def is_seen(job_id: str) -> bool:
    """이미 처리한 공고인지 확인한다."""
    with _conn() as con:
        row = con.execute(
            "SELECT 1 FROM seen_jobs WHERE job_id = ?", (job_id,)
        ).fetchone()
    return row is not None


def save_crawled(job: JobPosting) -> bool:
    """크롤링한 공고를 필터 대기(filtered=0) 상태로 저장한다.
    이미 존재하면 False를 반환한다."""
    with _conn() as con:
        cur = con.execute(
            """
            INSERT OR IGNORE INTO seen_jobs
                (job_id, title, company, url, is_matched, filtered, data_json, created_at)
            VALUES (?, ?, ?, ?, 0, 0, ?, ?)
            """,
            (
                job.job_id,
                job.title,
                job.company,
                job.url,
                json.dumps(asdict(job), ensure_ascii=False),
                datetime.now().isoformat(),
            ),
        )
        return cur.rowcount > 0


def get_unfiltered(limit: int) -> list[JobPosting]:
    """필터 미처리 공고를 오래된 순으로 최대 limit개 꺼낸다."""
    with _conn() as con:
        rows = con.execute(
            """
            SELECT data_json FROM seen_jobs
            WHERE filtered = 0 AND data_json IS NOT NULL
            ORDER BY created_at ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [JobPosting(**json.loads(r["data_json"])) for r in rows]


def mark_filtered(job_id: str, is_matched: bool) -> None:
    """AI 필터 처리 완료로 기록하고 매칭 결과를 갱신한다."""
    with _conn() as con:
        con.execute(
            "UPDATE seen_jobs SET filtered = 1, is_matched = ? WHERE job_id = ?",
            (int(is_matched), job_id),
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
        pending = con.execute("SELECT COUNT(*) FROM seen_jobs WHERE filtered = 0").fetchone()[0]
    return {"total": total, "matched": matched, "notified": notified, "pending": pending}
