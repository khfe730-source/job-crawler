import io
import logging
import os
import schedule
import sys
import time
from dotenv import load_dotenv

from config import (
    SCHEDULE_INTERVAL_HOURS,
    FILTER_INTERVAL_MINUTES,
    FILTER_BATCH_SIZE,
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

# 429 감지 시 True로 설정 → 다음 filter_once 1회 건너뛰기
_skip_next_filter: bool = False


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


def filter_once() -> None:
    """필터 대기 공고 중 FILTER_BATCH_SIZE개를 AI 판단 + 알림 처리한다.
    직전 사이클에 429 쿼터 초과가 감지되면 이번 실행은 건너뛴다."""
    global _skip_next_filter
    if _skip_next_filter:
        logger.warning("직전 사이클 쿼터 초과(429) 감지 → 이번 필터 건너뜀")
        _skip_next_filter = False
        return

    jobs = get_unfiltered(FILTER_BATCH_SIZE)
    if not jobs:
        logger.debug("필터 대기 공고 없음")
        return

    logger.info("=== 필터링 시작 (%d개) ===", len(jobs))
    matched_count = 0
    api_error_count = 0
    notification_count = 0

    for job in jobs:
        try:
            if USE_AI_FILTER:
                matched, reason = is_job_matching(job)
            else:
                matched, reason = check_excluded(job)
        except QuotaExceeded as e:
            _skip_next_filter = True
            logger.warning("쿼터 초과로 배치 중단, 다음 필터 사이클 건너뜀: %s", e)
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
            logger.info("최대 알림 한도 도달 (%d개), 나머지는 다음 사이클에 처리", MAX_NOTIFICATIONS_PER_RUN)
            break

    stats = get_stats()
    logger.info(
        "=== 필터링 완료 | 매칭: %d개, API 오류: %d개 | 누적: %s ===",
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

    # 시작 시 크롤링 1회 → 바로 첫 필터 실행
    crawl_once()
    filter_once()

    schedule.every(SCHEDULE_INTERVAL_HOURS).hours.do(crawl_once)
    schedule.every(FILTER_INTERVAL_MINUTES).minutes.do(filter_once)
    logger.info(
        "스케줄 등록: 크롤링 매 %d시간, 필터 매 %d분 (배치 %d개)",
        SCHEDULE_INTERVAL_HOURS,
        FILTER_INTERVAL_MINUTES,
        FILTER_BATCH_SIZE,
    )

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
