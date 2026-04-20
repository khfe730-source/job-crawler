import logging
import os
from slack_sdk.webhook import WebhookClient
from slack_sdk.errors import SlackApiError
from crawler import JobPosting
from config import PREFERRED_COMPANIES, LOG_ONLY, NOTIFY_UNMATCHED

logger = logging.getLogger(__name__)

_webhook: WebhookClient | None = None


def _get_webhook() -> WebhookClient:
    global _webhook
    if _webhook is None:
        url = os.environ.get("SLACK_WEBHOOK_URL", "")
        if not url:
            raise ValueError("SLACK_WEBHOOK_URL 환경변수가 설정되지 않았습니다.")
        _webhook = WebhookClient(url)
    return _webhook


def _is_preferred(company: str) -> bool:
    return any(pref in company for pref in PREFERRED_COMPANIES)


def _build_blocks(job: JobPosting, reason: str, matched: bool = True) -> list[dict]:
    star = " ⭐" if _is_preferred(job.company) else ""
    label = "[새 채용공고]" if matched else "[조건 불일치]"
    header_text = f"*{label}{star} {job.company}*"

    fields = [
        {"type": "mrkdwn", "text": f"*직무*\n{job.title}"},
        {"type": "mrkdwn", "text": f"*경력*\n{job.career}"},
        {"type": "mrkdwn", "text": f"*근무지*\n{job.location}"},
        {"type": "mrkdwn", "text": f"*마감일*\n{job.deadline}"},
    ]

    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": "🎮 GameJob 채용 알림" if matched else "❌ GameJob 조건 불일치"}},
        {"type": "section", "text": {"type": "mrkdwn", "text": header_text}},
        {"type": "section", "fields": fields},
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*{'AI 판단 이유' if matched else 'AI 불일치 이유'}*\n{reason}"},
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "공고 보러가기 →"},
                    "url": job.url,
                    "style": "primary",
                }
            ],
        },
        {"type": "divider"},
    ]

    return blocks


def _log_notification(job: JobPosting, reason: str, matched: bool = True) -> None:
    star = " ⭐" if _is_preferred(job.company) else ""
    label = "[공고 매칭]" if matched else "[조건 불일치]"
    logger.info(
        "%s%s %s | %s | %s | %s | %s",
        label, star, job.company, job.title, job.career, job.deadline, job.url,
    )
    if reason:
        logger.info("  └ 이유: %s", reason)


def send_job_notification(job: JobPosting, reason: str, matched: bool = True) -> bool:
    """채용공고 알림을 발송한다. LOG_ONLY=True면 로그로만 출력. 성공 여부 반환."""
    if LOG_ONLY:
        _log_notification(job, reason, matched)
        return True

    try:
        webhook = _get_webhook()
        blocks = _build_blocks(job, reason, matched)
        label = "[GameJob 알림]" if matched else "[GameJob 불일치]"
        response = webhook.send(
            text=f"{label} {job.company} - {job.title}",
            blocks=blocks,
        )
        if response.status_code != 200:
            logger.error("Slack 응답 오류 [%s]: %s", job.job_id, response.body)
            return False

        logger.info("Slack 알림 발송 완료: %s (%s)", job.title, job.company)
        return True

    except (SlackApiError, ValueError) as e:
        logger.error("Slack 알림 실패 [%s]: %s", job.job_id, e)
        return False
