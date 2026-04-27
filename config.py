"""
내 구직 조건 설정 파일.
이 파일을 수정해서 원하는 직무/경력/회사 조건을 설정하세요.
"""

# 희망 직무 키워드 (하나라도 포함되면 대상)
TARGET_JOBS = [
    "서버",
]

# 경력 조건
CAREER_MIN_YEARS = 0   # 최소 경력 (0 = 신입 포함)
CAREER_MAX_YEARS = None   # 최대 경력 (None = 제한 없음)
ACCEPT_NEWCOMER = False  # 신입 지원 가능 여부

# 선호 회사 키워드 (포함되면 우선순위 높음)
PREFERRED_COMPANIES = [
]

# 제외할 회사/키워드 (포함되면 무조건 제외)
EXCLUDED_KEYWORDS = [
]

# Gemini 모델 설정
GEMINI_MODEL = "gemini-2.5-flash-lite"

# AI 필터 활성화 여부
# False: EXCLUDED_KEYWORDS만 검사 후 검색 결과를 모두 Slack 발송 (AI 호출 없음)
# True: AI가 조건 부합 여부를 판단해 일치하는 공고만 발송
USE_AI_FILTER = True

# 알림 출력 방식
# True: Slack 대신 로그로만 출력 (테스트용, SLACK_WEBHOOK_URL 불필요)
# False: Slack Webhook으로 발송
LOG_ONLY = False

# AI 판단 시 추가 조건 (자유 형식)
ADDITIONAL_CONDITIONS = """
- 지원자는 게임 서버 개발자
- 기술 스택(상) : k8s, docker, aws, C++, C#, Argocd, Kustomize, Git, Agones, Karpenter
- 기술 스택(중) : jenkins, SVN, Claude, Cursor, MySQL, Redis, Prometheus, Grafana, ElasticSearch, Fluentd, Kibana (EFK), Cluster-autoscaler
- 기술 스택(하) : Golang, Python, MSSQL
- 근무지 판교, 강남 선호
"""

# AI 조건 불일치 공고도 Slack/로그로 출력 (AI 판단 검증용)
NOTIFY_UNMATCHED: bool = True

# 크롤링 설정
GAMEJOB_BASE_URL = "https://www.gamejob.co.kr"
CRAWL_PAGES = 3         # 키워드당 크롤링할 페이지 수 (TARGET_JOBS 키워드별 각각 적용)
REQUEST_DELAY = 1.5     # 요청 간 딜레이 (초)

# AI 필터 레이트리밋 (Gemini 2.5 Flash-Lite 무료 한도의 50% 기준)
# 실제 한도: RPM 30, RPD 1000, TPM 250000 → 보수 기준: RPM 15, RPD 500
# GitHub Actions cron(3시간마다, 8회/일) 기준으로 RPD 480 (500 한도 내) 안전 설계
AI_CALL_DELAY_SECONDS: float = 4.0   # AI 호출 간 딜레이 (초). 60/15=4초로 RPM 15 보장
MAX_AI_CALLS_PER_RUN: int = 60       # 1회 실행당 AI 호출 상한. 60×8회/일 = 480 RPD

# DB 설정
DB_PATH = "jobs.db"
