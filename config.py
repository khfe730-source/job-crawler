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
# 두 모델을 라운드로빈으로 교대 호출하여 모델별 RPD 한도(각 20)를 합산 활용
# (RPD/RPM 쿼터는 모델별로 독립이므로, 같은 키로 두 모델을 번갈아 호출하면 사실상 한도 2배)
GEMINI_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
]

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

# AI 필터 레이트리밋 (Gemini 무료 티어 모델별 RPD 20 한도 × 2모델 합산 운영)
# 운영 중 확인된 실제 enforce 한도: RPD 20 (quotaId: GenerateRequestsPerDayPerProjectPerModel-FreeTier, 모델별 독립)
# 호출은 GEMINI_MODELS 라운드로빈 → 각 모델은 절반의 호출만 수신하므로 실효 한도가 2배가 됨
# GitHub Actions cron(6시간마다, 4회/일) × 4건/회 = 일일 16건 (모델당 8건, 20 RPD 한도 내 안전 마진)
AI_CALL_DELAY_SECONDS: float = 2.0   # 호출 간 딜레이 (초). 라운드로빈이라 모델당 실효 4초 간격 → RPM 보호 유지
MAX_AI_CALLS_PER_RUN: int = 4        # 1회 실행당 AI 호출 상한 (2모델 × 2건). 4×4회/일 = 16건/일 (모델당 8건)

# DB 설정
DB_PATH = "jobs.db"
