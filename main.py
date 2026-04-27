import io
import logging
import os
import sys
import time
from dotenv import load_dotenv

from config import (
    AI_CALL_DELAY_SECONDS,
    MAX_AI_CALLS_PER_RUN,
    USE_AI_FILTER,
    LOG_ONLY,
    MAX_NOTIFICATIONS_PER_RUN,
    NOTIFY_UNMATCHED,
)
from crawler import crawl_jobs
from database import (
    init_db,
    save_crawled,
    get_unfiltered,
    mark_filtered,
    mark_notified,
    get_stats,
)
from ai_filter import is_job_matching, check_excluded, QuotaExceeded
from notifier import send_job_notification

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(
            io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
        )
    ],
)
logger = logging.getLogger(__name__)


def crawl_once() -> None:
    """크롤링만 수행하고 DB에 필터 대기 상태로 적재한다."""
    logger.info("=== 크롤링 시작 ===")
    jobs = crawl_jobs()

    new_count = 0
    for job in jobs:
        if save_crawled(job):
            new_count += 1

    stats = get_stats()
    logger.info(
        "=== 크롤링 완료 | 신규: %d개 | 누적 총계: %s ===",
        new_count,
        stats,
    )


def filter_pending() -> None:
    """필터 대기 공고를 처리한다.

    레이트리밋 가드:
    - RPM: AI 호출 간 AI_CALL_DELAY_SECONDS 대기 (Gemini RPM 15 준수)
    - RPD: 1회 실행당 최대 MAX_AI_CALLS_PER_RUN 호출
    - 429(QuotaExceeded) 발생 시 즉시 중단, 미처리 공고는 다음 cron 실행에서 처리
    """
    jobs = get_unfiltered(MAX_AI_CALLS_PER_RUN)
    if not jobs:
        logger.info("필터 대기 공고 없음")
        return

    logger.info(
        "=== 필터링 시작 | 대상 %d개 (회당 상한 %d) ===",
        len(jobs),
        MAX_AI_CALLS_PER_RUN,
    )

    matched_count = 0
    api_error_count = 0
    notification_count = 0
    ai_call_count = 0

    for index, job in enumerate(jobs):
        try:
            if USE_AI_FILTER:
                if ai_call_count > 0:
                    time.sleep(AI_CALL_DELAY_SECONDS)
                matched, reason = is_job_matching(job)
                ai_call_count += 1
            else:
                matched, reason = check_excluded(job)
        except QuotaExceeded as e:
            logger.warning(
                "쿼터 초과(429)로 중단 | 미처리 %d개는 다음 사이클에서 처리: %s",
                len(jobs) - index,
                e,
            )
            break

        # 일반 API 오류: 필터 완료로 기록하지 않고 다음 사이클에 재시도
        if matched is None:
            api_error_count += 1
            continue

        mark_filtered(job.job_id, matched)

        if matched:
            matched_count += 1
            if send_job_notification(job, reason, matched=True):
                mark_notified(job.job_id)
            notification_count += 1
        elif NOTIFY_UNMATCHED:
            send_job_notification(job, reason, matched=False)
            notification_count += 1

        if MAX_NOTIFICATIONS_PER_RUN and notification_count >= MAX_NOTIFICATIONS_PER_RUN:
            logger.info(
                "최대 알림 한도 도달 (%d개), 나머지는 다음 사이클에 처리",
                MAX_NOTIFICATIONS_PER_RUN,
            )
            break

    stats = get_stats()
    logger.info(
        "=== 필터링 완료 | AI 호출: %d, 매칭: %d, API 오류: %d | 누적: %s ===",
        ai_call_count,
        matched_count,
        api_error_count,
        stats,
    )


def main() -> None:
    load_dotenv()

    required = ["GEMINI_API_KEY"] if USE_AI_FILTER else []
    if not LOG_ONLY:
        required.append("SLACK_WEBHOOK_URL")
    missing = [v for v in required if not os.environ.get(v)]
    if missing:
        raise SystemExit(f"필수 환경변수 누락: {', '.join(missing)}\n.env 파일을 확인하세요.")

    init_db()
    crawl_once()
    filter_pending()
    logger.info("=== 실행 완료, 종료 ===")


if __name__ == "__main__":
    main()
