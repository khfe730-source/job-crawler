import logging
import os
import anthropic
from crawler import JobPosting
from config import (
    TARGET_JOBS,
    CAREER_MIN_YEARS,
    CAREER_MAX_YEARS,
    ACCEPT_NEWCOMER,
    PREFERRED_COMPANIES,
    EXCLUDED_KEYWORDS,
    ADDITIONAL_CONDITIONS,
)

logger = logging.getLogger(__name__)

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


def _build_prompt(job: JobPosting) -> str:
    conditions = f"""
희망 직무: {', '.join(TARGET_JOBS)}
경력 조건: {CAREER_MIN_YEARS}년 이상 ~ {CAREER_MAX_YEARS}년 이하 (신입 허용: {'예' if ACCEPT_NEWCOMER else '아니오'})
선호 회사: {', '.join(PREFERRED_COMPANIES)}
제외 키워드: {', '.join(EXCLUDED_KEYWORDS)}
추가 조건:
{ADDITIONAL_CONDITIONS}
""".strip()

    posting = f"""
공고 제목: {job.title}
회사명: {job.company}
경력 요건: {job.career}
근무지: {job.location}
마감일: {job.deadline}
태그: {', '.join(job.tags)}
공고 내용:
{job.description[:2000]}
""".strip()

    return f"""아래 채용공고가 구직자의 조건에 부합하는지 판단해주세요.

[구직자 조건]
{conditions}

[채용공고]
{posting}

판단 기준:
1. 직무가 구직자의 희망 직무와 관련 있는가
2. 경력 요건이 구직자 조건 범위 내인가
3. 제외 키워드가 포함되어 있지 않은가
4. 추가 조건을 고려했을 때 적합한가

반드시 아래 형식으로만 응답하세요:
RESULT: YES 또는 RESULT: NO
REASON: 판단 이유 (한 문장)"""


def check_excluded(job: JobPosting) -> tuple[bool, str]:
    """EXCLUDED_KEYWORDS 사전 검사. 제외 대상이면 (False, 이유) 반환."""
    full_text = f"{job.title} {job.description} {' '.join(job.tags)}"
    for kw in EXCLUDED_KEYWORDS:
        if kw in full_text:
            return False, f"제외 키워드 포함: {kw}"
    return True, ""


def is_job_matching(job: JobPosting) -> tuple[bool, str]:
    """Anthropic API로 공고가 조건에 맞는지 판단한다. (matched, reason) 반환"""
    passed, reason = check_excluded(job)
    if not passed:
        return False, reason

    prompt = _build_prompt(job)

    try:
        message = _get_client().messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        response_text = message.content[0].text.strip()
        logger.debug("AI 응답 [%s]: %s", job.job_id, response_text)

        matched = "RESULT: YES" in response_text
        reason = ""
        for line in response_text.splitlines():
            if line.startswith("REASON:"):
                reason = line.replace("REASON:", "").strip()
                break

        return matched, reason

    except anthropic.APIError as e:
        logger.error("Anthropic API 오류 [%s]: %s", job.job_id, e)
        return False, f"API 오류: {e}"
