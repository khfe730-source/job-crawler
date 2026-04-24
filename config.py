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
ACCEPT_NEWCOMER = True  # 신입 지원 가능 여부

# 선호 회사 키워드 (포함되면 우선순위 높음)
PREFERRED_COMPANIES = [
    "넥슨",
    "엔씨소프트",
    "넷마블",
    "크래프톤",
    "스마일게이트",
    "펄어비스",
    "카카오게임즈",
    "시프트업",
]

# 제외할 회사/키워드 (포함되면 무조건 제외)
EXCLUDED_KEYWORDS = [
    "일본어 필수",
    "중국어 필수",
]

# Gemini 모델 설정
GEMINI_MODEL = "gemini-2.5-flash"

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

# 1회 실행당 최대 알림 발송 수 (None = 제한 없음)
# 한도 초과 공고는 DB에 기록하지 않으므로 다음 사이클에 처리됨
MAX_NOTIFICATIONS_PER_RUN: int | None = 5

# 크롤링 설정
GAMEJOB_BASE_URL = "https://www.gamejob.co.kr"
CRAWL_PAGES = 3         # 키워드당 크롤링할 페이지 수 (TARGET_JOBS 키워드별 각각 적용)
REQUEST_DELAY = 1.5     # 요청 간 딜레이 (초)

# 스케줄 설정
SCHEDULE_INTERVAL_HOURS = 3      # 크롤링 실행 간격 (시간)
FILTER_INTERVAL_MINUTES = 5      # AI 필터 실행 간격 (분)
FILTER_BATCH_SIZE = 1            # 필터 1회당 처리 공고 수

# DB 설정
DB_PATH = "jobs.db"
