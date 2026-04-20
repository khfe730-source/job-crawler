import io
import logging
import os
import schedule
import sys
import time
from dotenv import load_dotenv

from config import SCHEDULE_INTERVAL_HOURS, USE_AI_FILTER, LOG_ONLY, MAX_NOTIFICATIONS_PER_RUN
from crawler import crawl_jobs
from database import init_db, is_seen, mark_seen, mark_notified, get_stats
from ai_filter import is_job_matching, check_excluded
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


def run_once() -> None:
    """크롤링 → AI 필터 → Slack 알림 한 사이클 실행."""
    logger.info("=== 채용공고 수집 시작 ===")

    jobs = crawl_jobs()
    new_count = 0
    matched_count = 0

    for job in jobs:
        if is_seen(job.job_id):
            continue
        new_count += 1

        if USE_AI_FILTER:
            matched, reason = is_job_matching(job)
        else:
            matched, reason = check_excluded(job)

        mark_seen(job.job_id, job.title, job.company, job.url, is_matched=matched)

        if matched:
            matched_count += 1
            if send_job_notification(job, reason):
                mark_notified(job.job_id)
            if MAX_NOTIFICATIONS_PER_RUN and matched_count >= MAX_NOTIFICATIONS_PER_RUN:
                logger.info("최대 알림 한도 도달 (%d개), 나머지는 다음 사이클에 처리", MAX_NOTIFICATIONS_PER_RUN)
                break

    stats = get_stats()
    logger.info(
        "=== 완료 | 신규: %d개, 조건 부합: %d개 | 누적 총계: %s ===",
        new_count,
        matched_count,
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

    # 첫 실행은 즉시
    run_once()

    # 이후 N시간마다 반복
    schedule.every(SCHEDULE_INTERVAL_HOURS).hours.do(run_once)
    logger.info("스케줄 등록: 매 %d시간마다 실행", SCHEDULE_INTERVAL_HOURS)

    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    main()
