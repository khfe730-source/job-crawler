import logging
import os
from google import genai
from google.genai import types
from google.genai import errors as genai_errors
from crawler import JobPosting


class QuotaExceeded(Exception):
    """Gemini API 쿼터(429 RESOURCE_EXHAUSTED) 초과 시 호출자가 전체 배치를 중단하도록 알리는 예외."""
from config import (
    TARGET_JOBS,
    PREFERRED_COMPANIES,
    EXCLUDED_KEYWORDS,
    ADDITIONAL_CONDITIONS,
)

logger = logging.getLogger(__name__)

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    return _client


def _build_prompt(job: JobPosting) -> str:
    conditions = f"""
희망 직무: {', '.join(TARGET_JOBS)}
선호 회사: {', '.join(PREFERRED_COMPANIES)}
제외 키워드: {', '.join(EXCLUDED_KEYWORDS)}
추가 조건:
{ADDITIONAL_CONDITIONS}
""".strip()

    posting = f"""
공고 제목: {job.title}
회사명: {job.company}
태그: {', '.join(job.tags)}
공고 내용:
{job.description[:2000]}
""".strip()

    return f"""아래 채용공고가 구직자의 조건에 부합하는지 판단하고, 공고에서 정보를 추출해주세요.

[구직자 조건]
{conditions}

[채용공고]
{posting}

판단 기준:
1. 직무가 구직자의 희망 직무와 관련 있는가
2. 제외 키워드가 포함되어 있지 않은가
3. 추가 조건을 고려했을 때 적합한가

반드시 아래 형식으로만 응답하세요:
RESULT: YES 또는 RESULT: NO
REASON: 판단 이유 (한 문장)
CAREER: 경력 요건 (공고 내용에서 추출. 없으면 정보 없음)
LOCATION: 근무지 (공고 내용에서 추출. 없으면 정보 없음)
DEADLINE: 마감일 (공고 내용에서 추출. 없으면 정보 없음)"""


def check_excluded(job: JobPosting) -> tuple[bool, str]:
    """EXCLUDED_KEYWORDS 사전 검사. 제외 대상이면 (False, 이유) 반환."""
    full_text = f"{job.title} {job.description} {' '.join(job.tags)}"
    for kw in EXCLUDED_KEYWORDS:
        if kw in full_text:
            return False, f"제외 키워드 포함: {kw}"
    return True, ""


def is_job_matching(job: JobPosting, model: str) -> tuple[bool | None, str]:
    """Gemini API로 공고가 조건에 맞는지 판단한다.
    호출자가 사용할 모델(`model`)을 명시적으로 전달 — config.GEMINI_MODELS 라운드로빈 분배를 위해.
    (True/False, reason) 반환. 일반 API 오류 시 (None, 오류메시지) — 호출자는 DB 기록/알림을 건너뛰어 다음 사이클에 재시도하도록 함.
    429 쿼터 초과 시 QuotaExceeded 예외를 올려 현재 배치를 즉시 중단시킨다."""
    passed, reason = check_excluded(job)
    if not passed:
        return False, reason

    prompt = _build_prompt(job)

    try:
        response = _get_client().models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(max_output_tokens=400),
        )
        response_text = response.text.strip()
        logger.info("AI 응답 [%s/%s]: %s", model, job.job_id, response_text)

        matched = "RESULT: YES" in response_text
        reason = ""
        for line in response_text.splitlines():
            if line.startswith("REASON:"):
                reason = line.replace("REASON:", "").strip()
            elif line.startswith("CAREER:"):
                job.career = line.replace("CAREER:", "").strip()
            elif line.startswith("LOCATION:"):
                job.location = line.replace("LOCATION:", "").strip()
            elif line.startswith("DEADLINE:"):
                job.deadline = line.replace("DEADLINE:", "").strip()

        return matched, reason

    except genai_errors.APIError as e:
        if getattr(e, "code", None) == 429:
            logger.warning("Gemini 쿼터 초과 [%s/%s]: %s", model, job.job_id, getattr(e, "message", e))
            raise QuotaExceeded(str(e)) from e
        logger.error("Gemini API 오류 [%s/%s]: %s", model, job.job_id, e)
        return None, f"API 오류: {e}"
    except Exception as e:
        logger.error("Gemini API 오류 [%s/%s]: %s", model, job.job_id, e)
        return None, f"API 오류: {e}"
