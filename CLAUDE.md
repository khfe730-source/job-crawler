# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 개요

gamejob.co.kr 채용공고를 주기적으로 크롤링하여 Anthropic AI로 조건 부합 여부를 판단하고, 조건에 맞는 공고를 Slack으로 알림하는 봇.

## 실행 방법

```bash
# 의존성 설치
pip install -r requirements.txt

# .env 파일 생성
cp .env.example .env
# .env에 ANTHROPIC_API_KEY, SLACK_WEBHOOK_URL 입력

# 실행 (즉시 1회 수집 후 3시간마다 반복)
python main.py
```

## 아키텍처

파이프라인 흐름: `main.py` → `crawler.py` → `database.py` → `ai_filter.py` → `notifier.py`

| 파일 | 역할 |
|------|------|
| `config.py` | 직무/경력/선호 회사 조건 + 크롤링/스케줄 설정 전체 |
| `crawler.py` | requests + BeautifulSoup으로 목록/상세 페이지 파싱, `JobPosting` dataclass 반환 |
| `database.py` | SQLite `seen_jobs` 테이블로 중복 방지, 매칭·발송 상태 관리 |
| `ai_filter.py` | claude-haiku-4-5에 config 조건을 프롬프트로 전달, YES/NO + 이유 파싱 |
| `notifier.py` | Slack Block Kit 카드 발송, 선호 회사 ⭐ 표시 |
| `main.py` | 파이프라인 조율, `schedule` 라이브러리로 3시간 반복 |

## 주요 설정 변경

구직 조건은 **`config.py`만 수정**하면 됨:
- `TARGET_JOBS` — 희망 직무 키워드
- `CAREER_MIN_YEARS` / `CAREER_MAX_YEARS` — 경력 범위
- `PREFERRED_COMPANIES` — 선호 회사 목록 (Slack 알림에 ⭐ 표시)
- `EXCLUDED_KEYWORDS` — 이 키워드가 공고에 있으면 무조건 제외
- `ADDITIONAL_CONDITIONS` — AI 프롬프트에 자유 형식으로 추가 조건 기술
- `CRAWL_PAGES` — 크롤링할 페이지 수 (기본 3)
- `SCHEDULE_INTERVAL_HOURS` — 실행 간격 (기본 3시간)

## 환경변수

`.env` 파일에 설정 (`.env.example` 참고):
- `ANTHROPIC_API_KEY` — Anthropic API 키
- `SLACK_WEBHOOK_URL` — Slack Incoming Webhook URL

## gamejob.co.kr 파싱 특이사항

- 인코딩: EUC-KR (`resp.encoding = "euc-kr"` 명시 필요)
- 공고 ID: URL 쿼리스트링의 `GIJP_No` 또는 `GI_No` 파라미터
- 목록 셀렉터: `table.list_tb tbody tr` / 상세 본문: `div.view_cont`
- 사이트 구조 변경 시 `crawler.py`의 CSS 셀렉터 수정

## AI 필터 동작 방식

1. `EXCLUDED_KEYWORDS`는 API 호출 없이 사전 검사로 제외 (비용 절감)
2. 통과한 공고만 claude-haiku API 호출 → `RESULT: YES/NO` + `REASON:` 파싱
3. AI 모델 변경 시 `ai_filter.py`의 `model` 파라미터 수정
