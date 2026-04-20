import logging
import os
import schedule
import time
from dotenv import load_dotenv

from config import SCHEDULE_INTERVAL_HOURS
from crawler import crawl_jobs
from database import init_db, is_seen, mark_seen, mark_notified, get_stats
from ai_filter import is_job_matching
from notifier import send_job_notification

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def run_once() -> None:
    """크롤링 → AI 필터 → Slack 알림 한 사이클 실행."""
    logger.info("=== 채용공고 수집 시작 ===")

    jobs = crawl_jobs()
    new_count = 0
    pre_filtered_count = 0
    matched_count = 0

    for job in jobs:
        if is_seen(job.job_id):
            continue
        new_count += 1

        if job.pre_filtered:
            pre_filtered_count += 1
            mark_seen(job.job_id, job.title, job.company, job.url, is_matched=False)
            continue

        matched, reason = is_job_matching(job)
        mark_seen(job.job_id, job.title, job.company, job.url, is_matched=matched)

        if matched:
            matched_count += 1
            if send_job_notification(job, reason):
                mark_notified(job.job_id)

    stats = get_stats()
    logger.info(
        "=== 완료 | 신규: %d개 (제목 필터 제외: %d개, AI 검토: %d개), 조건 부합: %d개 | 누적 총계: %s ===",
        new_count,
        pre_filtered_count,
        new_count - pre_filtered_count,
        matched_count,
        stats,
    )


def main() -> None:
    load_dotenv()

    missing = [v for v in ("ANTHROPIC_API_KEY", "SLACK_WEBHOOK_URL") if not os.environ.get(v)]
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
