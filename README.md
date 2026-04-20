# gamejob-bot

gamejob.co.kr 채용공고를 주기적으로 크롤링하여 Anthropic AI로 조건 부합 여부를 판단하고, 조건에 맞는 공고를 Slack으로 알림하는 봇.

## 동작 방식

크롤링과 AI 필터링이 **독립된 스케줄**로 동작합니다 (Gemini 무료 티어 한도를 분산 소진하기 위함).

**크롤링 스케줄** (`SCHEDULE_INTERVAL_HOURS`, 기본 3시간):
1. `TARGET_JOBS` 키워드별로 gamejob.co.kr 검색 API 호출
2. 공고 ID로 중복 제거 후 상세 페이지까지 수집
3. 신규 공고를 SQLite DB에 `filtered=0`(필터 대기)로 적재

**필터 스케줄** (`FILTER_INTERVAL_MINUTES`, 기본 5분 / `FILTER_BATCH_SIZE`, 기본 5개):
1. 필터 대기 공고를 오래된 순으로 배치만큼 꺼냄
2. `EXCLUDED_KEYWORDS` 사전 검사 (API 호출 없이 제외)
3. Gemini AI가 구직 조건 부합 여부 판단
4. 결과를 Slack Block Kit 카드로 발송 (선호 회사는 ⭐ 표시)
5. 처리 완료 공고는 `filtered=1`로 표시, API 오류는 다음 사이클 재시도

## 요구사항

- Python 3.9+
- Google Gemini API 키 (무료)
- Slack Incoming Webhook URL

## 설치 방법

```bash
# 저장소 클론
git clone <repo-url>
cd gamejob-bot

# 의존성 설치
pip install -r requirements.txt
```

## 환경변수 설정

`.env.example`을 복사하여 `.env` 파일을 생성하고 값을 입력합니다.

```bash
cp .env.example .env
```

`.env` 파일:

```env
GEMINI_API_KEY=your_gemini_api_key_here
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/your/webhook/url
```

| 변수 | 설명 |
|------|------|
| `GEMINI_API_KEY` | [Google AI Studio](https://aistudio.google.com/app/apikey)에서 무료 발급 |
| `SLACK_WEBHOOK_URL` | Slack 앱 설정 > Incoming Webhooks에서 발급 |

## 실행 방법

```bash
# 즉시 크롤링 + 첫 필터 1회 실행 → 이후 각 스케줄로 반복
python main.py
```

실행 시 동작 순서:
1. `.env` 파일에서 환경변수 로드 및 유효성 검사
2. SQLite DB 초기화 및 마이그레이션 (`jobs.db` 자동 생성)
3. 즉시 크롤링 1회 → 바로 첫 필터 배치 1회 실행
4. 이후 `SCHEDULE_INTERVAL_HOURS`마다 크롤링, `FILTER_INTERVAL_MINUTES`마다 필터 배치 반복

> **종료:** `Ctrl+C`로 언제든 중단 가능. 재시작 시 DB에 저장된 공고는 중복 발송되지 않음.

## 사용 방법

### 1단계: 구직 조건 설정

`config.py`를 열어 본인 조건에 맞게 수정합니다.

```python
# 희망 직무 키워드 — 하나라도 포함된 공고가 크롤링 대상
TARGET_JOBS = ["게임 기획", "레벨 디자이너", "콘텐츠 기획"]

# 경력 범위
CAREER_MIN_YEARS = 0    # 0이면 신입 포함
CAREER_MAX_YEARS = 5    # None이면 상한 없음
ACCEPT_NEWCOMER = True  # 신입 공고 허용 여부

# 선호 회사 — Slack 알림에 ⭐ 표시됨
PREFERRED_COMPANIES = ["넥슨", "크래프톤", "엔씨소프트"]

# 제외 키워드 — 해당 키워드가 있으면 AI 호출 없이 즉시 제외 (비용 절감)
EXCLUDED_KEYWORDS = ["일본어 필수", "중국어 필수"]

# AI에게 전달할 추가 조건 (자유 형식 텍스트)
ADDITIONAL_CONDITIONS = """
- 재택근무 또는 하이브리드 근무 가능한 회사 선호
- RPG, 액션 장르 프로젝트 선호
"""

# 키워드당 크롤링할 페이지 수 (TARGET_JOBS 키워드별 각각 적용)
CRAWL_PAGES = 3

# 자동 반복 간격 (시간)
SCHEDULE_INTERVAL_HOURS = 3
```

### 2단계: 실행 및 로그 확인

```bash
python main.py
```

정상 실행 시 아래와 같은 로그가 출력됩니다:

```
2026-04-20 10:00:00 [INFO] __main__: === 채용공고 수집 시작 ===
2026-04-20 10:00:05 [INFO] __main__: === 완료 | 신규: 12개, 조건 부합: 3개 | 누적 총계: ... ===
2026-04-20 10:00:05 [INFO] __main__: 스케줄 등록: 매 3시간마다 실행
```

### 3단계: Slack 알림 확인

조건에 맞는 공고는 Slack 채널에 Block Kit 카드 형식으로 전송됩니다.
- 선호 회사(`PREFERRED_COMPANIES`) 공고에는 ⭐ 표시
- 카드에는 회사명, 직무, 경력, 마감일, 공고 링크, AI 판단 이유 포함

### 조건 변경 후 재실행

`config.py`를 수정한 뒤 프로세스를 재시작하면 변경 조건이 즉시 적용됩니다.
이미 수집된 공고(DB에 기록된 것)는 재평가하지 않으므로, 과거 공고를 다시 검사하려면 `jobs.db`를 삭제하고 재실행하세요.

```bash
rm jobs.db && python main.py
```

## 구직 조건 설정

`config.py` 파일만 수정하면 됩니다.

```python
# 희망 직무 키워드
TARGET_JOBS = ["백엔드", "서버", "Python"]

# 경력 범위 (년)
CAREER_MIN_YEARS = 2
CAREER_MAX_YEARS = 7

# 선호 회사 목록 (Slack 알림에 ⭐ 표시)
PREFERRED_COMPANIES = ["넥슨", "크래프톤", "엔씨소프트"]

# 이 키워드가 공고에 있으면 무조건 제외 (API 호출 없이 처리)
EXCLUDED_KEYWORDS = ["신입", "인턴", "게임 클라이언트"]

# AI 프롬프트에 추가할 자유 형식 조건
ADDITIONAL_CONDITIONS = "재택근무 가능한 포지션 선호"

# 크롤링할 페이지 수
CRAWL_PAGES = 3

# 크롤링 간격 (시간)
SCHEDULE_INTERVAL_HOURS = 3

# AI 필터 간격 (분) / 필터 1회당 처리 공고 수
FILTER_INTERVAL_MINUTES = 5
FILTER_BATCH_SIZE = 5
```

## 폴더 구조

```
gamejob-bot/
├── main.py            # 파이프라인 조율, 스케줄 반복 실행
├── config.py          # 구직 조건 및 크롤링/스케줄 설정 전체
├── crawler.py         # gamejob.co.kr 목록/상세 페이지 파싱
├── database.py        # SQLite 중복 방지, 매칭·발송 상태 관리
├── ai_filter.py       # Claude Haiku AI 조건 판단
├── notifier.py        # Slack Block Kit 알림 발송
├── requirements.txt   # Python 의존성
├── .env.example       # 환경변수 템플릿
└── .env               # 환경변수 (gitignore됨)
```

## 파이프라인 흐름

```
main.py → crawler.py → database.py → ai_filter.py → notifier.py
```

| 파일 | 역할 |
|------|------|
| `config.py` | 직무/경력/선호 회사 조건 + 크롤링/스케줄 설정 전체 |
| `crawler.py` | requests + BeautifulSoup으로 목록/상세 페이지 파싱, `JobPosting` dataclass 반환 |
| `database.py` | SQLite `seen_jobs` 테이블로 중복 방지, 매칭·발송 상태 관리 |
| `ai_filter.py` | Gemini API에 config 조건을 프롬프트로 전달, YES/NO + 이유 파싱 |
| `notifier.py` | Slack Block Kit 카드 발송, 선호 회사 ⭐ 표시 |
| `main.py` | 크롤링과 필터링을 별도 스케줄(`SCHEDULE_INTERVAL_HOURS` / `FILTER_INTERVAL_MINUTES`)로 반복 |
