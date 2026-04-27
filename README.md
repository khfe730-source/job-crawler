# gamejob-bot

gamejob.co.kr 채용공고를 주기적으로 크롤링하여 Gemini AI로 조건 부합 여부를 판단하고, 조건에 맞는 공고를 Slack으로 알림하는 봇.

## 동작 방식

프로그램은 **1회 실행 후 종료**하는 구조입니다. 주기적 실행은 GitHub Actions cron(현재 6시간 간격)이 담당합니다.

**1회 실행 흐름:**
1. **크롤링** — `TARGET_JOBS` 키워드별로 gamejob.co.kr 검색 → 중복 제거 후 상세 페이지 수집 → SQLite DB에 `filtered=0`(필터 대기)로 적재
2. **AI 필터링** — 필터 대기 공고를 오래된 순으로 최대 `MAX_AI_CALLS_PER_RUN`건 처리
   - `EXCLUDED_KEYWORDS` 사전 검사 (API 호출 없이 제외)
   - Gemini AI가 구직 조건 부합 여부 판단 (호출 간 `AI_CALL_DELAY_SECONDS` 대기로 RPM 준수)
   - 결과를 Slack Block Kit 카드로 발송 (선호 회사는 ⭐ 표시)
   - 처리 완료 공고는 `filtered=1`로 표시, API 오류/429는 다음 cron 실행에서 재시도

**Gemini 무료 티어 실제 enforced 한도 대응 설계:**
- 운영 중 확인된 실제 RPD: 20 (공식 문서 1,000과 다름)
- RPM 보호: 호출 간 `AI_CALL_DELAY_SECONDS=4`초 sleep
- RPD 보호: 회당 `MAX_AI_CALLS_PER_RUN=2`건 × 4회/일(6시간 간격) = 8건/일

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
# 1회 크롤링 + 필터링 후 종료
python main.py
```

실행 시 동작 순서:
1. `.env` 파일에서 환경변수 로드 및 유효성 검사
2. SQLite DB 초기화 및 마이그레이션 (`jobs.db` 자동 생성)
3. 크롤링 1회 → 필터 대기 공고 처리(최대 `MAX_AI_CALLS_PER_RUN`건) → 종료

> **주기 실행:** GitHub Actions cron(현재 6시간마다)으로 반복 실행. 미처리 공고는 다음 cron 실행에서 자동으로 이어받음.

## GitHub Actions 운영

`.github/workflows/crawl.yml`이 6시간마다 자동 실행됩니다.

**Secrets 설정** (Repo Settings → Secrets and variables → Actions):
- `GEMINI_API_KEY` — Gemini API 키
- `SLACK_WEBHOOK_URL` — Slack Webhook URL

**수동 실행**:
- Actions 탭 → "Crawl Jobs" workflow → Run workflow 버튼

**DB 영속성**:
- `actions/cache@v4`로 `jobs.db`를 캐시 저장/복원 (키: `jobs-db-${run_id}`, 복원: `jobs-db-` prefix 매칭)
- 7일간 미실행 시 캐시 만료 → DB 초기화되어 누적 공고가 신규로 재인식됨 (6시간 cron이라 발생 가능성 낮음)

**스케줄 변경**: `.github/workflows/crawl.yml`의 `cron` 표현식 수정 (UTC 기준)

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
```

### 2단계: 실행 및 로그 확인

```bash
python main.py
```

정상 실행 시 아래와 같은 로그가 출력됩니다:

```
2026-04-20 10:00:00 [INFO] __main__: === 크롤링 시작 ===
2026-04-20 10:00:05 [INFO] __main__: === 크롤링 완료 | 신규: 12개 | 누적 총계: ... ===
2026-04-20 10:00:05 [INFO] __main__: === 필터링 시작 | 대상 12개 (회당 상한 60) ===
2026-04-20 10:01:00 [INFO] __main__: === 필터링 완료 | AI 호출: 12, 매칭: 3, API 오류: 0 | 누적: ... ===
2026-04-20 10:01:00 [INFO] __main__: === 실행 완료, 종료 ===
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

# AI 필터 레이트리밋 (Gemini 무료 티어 실제 RPD 20 한도 대응)
AI_CALL_DELAY_SECONDS = 4.0   # 호출 간 딜레이 (RPM 보호)
MAX_AI_CALLS_PER_RUN = 2      # 1회 실행당 AI 호출 상한 (4회/일 cron × 2 = 8건/일)
```

## 폴더 구조

```
gamejob-bot/
├── main.py            # 파이프라인 조율, 1회 실행 후 종료
├── config.py          # 구직 조건 및 크롤링/레이트리밋 설정 전체
├── crawler.py         # gamejob.co.kr 목록/상세 페이지 파싱
├── database.py        # SQLite 중복 방지, 매칭·발송 상태 관리
├── ai_filter.py       # Gemini AI 조건 판단
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
| `config.py` | 직무/경력/선호 회사 조건 + 크롤링/레이트리밋 설정 전체 |
| `crawler.py` | requests + BeautifulSoup으로 목록/상세 페이지 파싱, `JobPosting` dataclass 반환 |
| `database.py` | SQLite `seen_jobs` 테이블로 중복 방지, 매칭·발송 상태 관리 |
| `ai_filter.py` | Gemini API에 config 조건을 프롬프트로 전달, YES/NO + 이유 파싱 |
| `notifier.py` | Slack Block Kit 카드 발송, 선호 회사 ⭐ 표시 |
| `main.py` | 1회 실행으로 크롤링 → 필터링 수행 후 종료 (스케줄링은 GitHub Actions cron) |
