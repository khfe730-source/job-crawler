"""
내 구직 조건 설정 파일.
이 파일을 수정해서 원하는 직무/경력/회사 조건을 설정하세요.
"""

# 희망 직무 키워드 (하나라도 포함되면 대상)
TARGET_JOBS = [
    "게임 기획",
    "레벨 디자이너",
    "콘텐츠 기획",
    "시스템 기획",
    "게임 디자이너",
]

# 경력 조건
CAREER_MIN_YEARS = 0   # 최소 경력 (0 = 신입 포함)
CAREER_MAX_YEARS = 5   # 최대 경력 (None = 제한 없음)
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

# AI 판단 시 추가 조건 (자유 형식)
ADDITIONAL_CONDITIONS = """
- 재택근무 또는 하이브리드 근무 가능한 회사 선호
- 인디/소규모 스튜디오보다 중견 이상 회사 선호
- RPG, 액션 장르 프로젝트 선호
"""

# 크롤링 설정
GAMEJOB_BASE_URL = "https://www.gamejob.co.kr"
GAMEJOB_LIST_URL = "https://www.gamejob.co.kr/List_GI/GIB_List.asp"
CRAWL_PAGES = 3         # 크롤링할 페이지 수
REQUEST_DELAY = 1.5     # 요청 간 딜레이 (초)

# 스케줄 설정
SCHEDULE_INTERVAL_HOURS = 3  # 자동 실행 간격 (시간)

# DB 설정
DB_PATH = "jobs.db"
