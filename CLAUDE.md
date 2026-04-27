# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 개발 환경

- **Python 3.14.4** 사용 — 코드 작성 시 이 버전의 문법과 표준 라이브러리 기준으로 작성할 것
- 3.14에서 추가된 기능(타입 힌트 개선, 새 표준 라이브러리 등) 적극 활용 가능
- 하위 버전 호환성 고려 불필요

## 프로젝트 개요

gamejob.co.kr 채용공고를 주기적으로 크롤링하여 Anthropic AI로 조건 부합 여부를 판단하고, 조건에 맞는 공고를 Slack으로 알림하는 봇.

## 실행 방법

```bash
# 의존성 설치
pip install -r requirements.txt

# .env 파일 생성
cp .env.example .env
# .env에 GEMINI_API_KEY, SLACK_WEBHOOK_URL 입력

# 1회 실행 후 종료 (주기 실행은 GitHub Actions cron이 담당)
python main.py
```

## 아키텍처

파이프라인 흐름: `main.py` → `crawler.py` → `database.py` → `ai_filter.py` → `notifier.py`

| 파일 | 역할 |
|------|------|
| `config.py` | 직무/경력/선호 회사 조건 + 크롤링/레이트리밋 설정 전체 |
| `crawler.py` | requests + BeautifulSoup으로 목록/상세 페이지 파싱, `JobPosting` dataclass 반환 |
| `database.py` | SQLite `seen_jobs` 테이블로 중복 방지, 매칭·발송 상태 관리 |
| `ai_filter.py` | Gemini API에 config 조건을 프롬프트로 전달, YES/NO + 이유 파싱 |
| `notifier.py` | Slack Block Kit 카드 발송, 선호 회사 ⭐ 표시 |
| `main.py` | 1회 실행으로 크롤링 → AI 필터링 수행 후 종료 (스케줄링은 GitHub Actions cron) |

## 주요 설정 변경

구직 조건은 **`config.py`만 수정**하면 됨:
- `TARGET_JOBS` — 희망 직무 키워드
- `CAREER_MIN_YEARS` / `CAREER_MAX_YEARS` — 경력 범위
- `PREFERRED_COMPANIES` — 선호 회사 목록 (Slack 알림에 ⭐ 표시)
- `EXCLUDED_KEYWORDS` — 이 키워드가 공고에 있으면 무조건 제외
- `ADDITIONAL_CONDITIONS` — AI 프롬프트에 자유 형식으로 추가 조건 기술
- `CRAWL_PAGES` — 크롤링할 페이지 수 (기본 3)
- `AI_CALL_DELAY_SECONDS` / `MAX_AI_CALLS_PER_RUN` — Gemini 레이트리밋 가드 (기본 4초 / 60건)
- 주기 실행 간격은 GitHub Actions workflow의 cron으로 설정 (권장 3시간)

## 환경변수

`.env` 파일에 설정 (`.env.example` 참고):
- `GEMINI_API_KEY` — Google AI Studio에서 무료 발급
- `SLACK_WEBHOOK_URL` — Slack Incoming Webhook URL

## gamejob.co.kr 파싱 특이사항

- 인코딩: 서버 Content-Type charset을 우선 사용, charset 없으면 `resp.apparent_encoding`으로 자동 감지 (구 ASP 페이지는 EUC-KR, 신규 페이지는 UTF-8)
- 공고 ID: `<a href="/Recruit/GI_Read/View?GI_No=N">` URL의 `GI_No` 파라미터
- 목록 파싱: `GI_No=` 포함 `<a>` 태그 기준으로 부모 `<tr>` 셀 추출 (클래스 의존 없음)
- 상세 본문: `div.view_cont` → `div.recruit_view` → `div#contents` 순으로 fallback
- 페이지네이션: 1페이지는 검색 URL 직접, 2페이지~는 세션 유지 후 `/recruit/_GI_Job_List?Page=N`

## 크롤링 방식

- `TARGET_JOBS` 각 키워드를 gamejob 검색 URL(`/Recruit/joblist?menucode=searchtot&searchtype=all&searchstring=[keyword]`)로 개별 검색
- `requests.Session`으로 세션 유지 → 이후 페이지는 `/recruit/_GI_Job_List?Page=N` AJAX 엔드포인트 사용
- 키워드별 결과를 `job_id`로 중복 제거 후 합산
- 공고 HTML 파싱: `<a href="/Recruit/GI_Read/View?GI_No=N">` 링크 기준, 부모 `<tr>` 셀에서 회사명/경력 추출

## AI 필터 동작 방식

1. `EXCLUDED_KEYWORDS`는 API 호출 없이 사전 검사로 제외 (비용 절감)
2. 통과한 공고만 Gemini API 호출 → `RESULT: YES/NO` + `REASON:` 파싱
3. AI 모델 변경 시 `ai_filter.py`의 `model` 파라미터 수정

### Gemini 2.5 Flash-Lite 무료 한도 (보수적 기준 — 실제 한도의 50%)

| 항목 | 실제 한도 | 사용 목표 (50%) |
|------|-----------|----------------|
| RPM (분당 요청) | 30 | **15 RPM** |
| RPD (일일 요청) | 1,000 | **500 RPD** |
| TPM (분당 토큰) | 250,000 | **125,000 TPM** |

크롤링/필터링 구조 설계 시 아래 기준을 준수할 것:
- 공고 1건당 API 호출 1회 기준, **1회 실행에서 최대 처리 공고 수 = 500 RPD 내 일일 누적 호출을 고려해 설정**
- 연속 호출 시 분당 15건을 초과하지 않도록 호출 간 딜레이(`time.sleep`) 또는 배치 크기 조절
- `QuotaExceeded` (429) 발생 시 즉시 중단, 미처리 공고는 다음 실행 사이클에서 재처리

## 테스트 규칙

별도 언급이 없는 한 테스트는 항상 아래 조건으로 실행할 것:

- 가상환경(venv) 활성화 후 실행: `source venv/Scripts/activate && python main.py`
- `USE_AI_FILTER = False` — AI 호출 없이 실행
- `LOG_ONLY = True` — Slack 미발송, 로그 출력으로 확인

테스트 전 config.py에서 위 두 값을 확인하고, 다르면 변경 후 실행.
테스트 완료 후 원래 설정으로 되돌릴 것.

## 원격 저장소 반영 규칙

원격 저장소(`origin`)에 변경사항을 올릴 때는 **절대 `main`/`master` 브랜치에 직접 push하지 말 것.**

반드시 아래 순서로 진행:

1. 작업 브랜치 생성 후 커밋: `git checkout -b <branch-name>`
2. 브랜치 push: `git push -u origin <branch-name>`
3. PR 생성: `gh pr create` 로 Pull Request 열기
4. **PR 승인 및 머지는 사용자가 직접 수행** — Claude는 머지하지 않음

PR 생성 후 URL을 사용자에게 알려주고 작업 종료.

## 작업 완료 후 PR 생성 규칙

**모든 작업이 완료되면 즉시 PR을 생성할 것.** 사용자가 별도로 요청하지 않아도 아래를 자동으로 수행:

1. 변경 파일 커밋 (작업 완료 후 Git 커밋 규칙 준수)
2. 브랜치 push
3. `gh pr create`로 PR 생성
4. PR URL을 사용자에게 전달하며 작업 종료

## 작업 완료 후 Git 커밋 규칙

작업이 끝날 때마다 반드시 아래 순서로 진행할 것:

1. 가상환경에서 import 확인으로 컴파일 오류 검사:
   ```bash
   source venv/Scripts/activate && python -c "import main"
   ```
2. 오류 없으면 커밋 진행. 오류 있으면 수정 후 재확인.

커밋 명령:

```bash
git add <변경된 파일>
git commit -m "<type>: <변경 내용 요약>"
```

- 커밋 타입: `feat` (기능), `fix` (버그), `refactor` (리팩토링), `docs` (문서), `chore` (설정)
- 커밋 단위: 논리적으로 하나의 작업 단위마다 1커밋 (여러 파일이라도 같은 목적이면 한 커밋)
- 커밋 메시지: 한국어 또는 영어 통일, 무엇을 왜 했는지 명확히 기술

## README.md 유지 규칙

아래 항목이 변경될 경우 반드시 `README.md`도 함께 수정할 것:
- `config.py` — 설정 항목 추가/삭제/변경 시 "구직 조건 설정" 섹션 업데이트
- `requirements.txt` — 의존성 변경 시 "요구사항" 섹션 업데이트
- `.env.example` — 환경변수 추가/삭제 시 "환경변수 설정" 섹션 업데이트
- 파일 추가/삭제 시 "폴더 구조" 및 "파이프라인 흐름" 섹션 업데이트
- 실행 방법 변경 시 "실행 방법" 섹션 업데이트
