import time
import logging
import requests
from bs4 import BeautifulSoup
from dataclasses import dataclass, field
from typing import Optional
from config import (
    GAMEJOB_BASE_URL,
    GAMEJOB_LIST_URL,
    CRAWL_PAGES,
    REQUEST_DELAY,
    TARGET_JOBS,
    PREFILTER_BY_TITLE,
)

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Referer": GAMEJOB_BASE_URL,
}


@dataclass
class JobPosting:
    job_id: str
    title: str
    company: str
    career: str
    location: str
    deadline: str
    url: str
    description: str = ""
    tags: list[str] = field(default_factory=list)
    pre_filtered: bool = False  # 제목 사전 필터에서 제외됨 (상세 미조회)


def _passes_title_filter(title: str) -> bool:
    """TARGET_JOBS의 키워드 단어가 하나라도 제목에 포함되면 True."""
    for kw in TARGET_JOBS:
        if kw in title:
            return True
        for word in kw.split():
            if len(word) >= 2 and word in title:
                return True
    return False


def _fetch_page(page: int) -> Optional[BeautifulSoup]:
    """주어진 페이지 번호의 채용공고 목록을 가져온다."""
    params = {
        "schWork": "",
        "schCate": "",
        "schKeyword": " ".join(TARGET_JOBS[:3]),  # 주요 키워드로 검색
        "Page_No": page,
    }
    try:
        resp = requests.get(GAMEJOB_LIST_URL, params=params, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        resp.encoding = "euc-kr"
        return BeautifulSoup(resp.text, "lxml")
    except requests.RequestException as e:
        logger.error("페이지 %d 요청 실패: %s", page, e)
        return None


def _parse_list_page(soup: BeautifulSoup) -> list[dict]:
    """목록 페이지에서 공고 기본 정보를 파싱한다."""
    postings = []

    rows = soup.select("table.list_tb tbody tr")
    for row in rows:
        cells = row.select("td")
        if len(cells) < 5:
            continue

        title_tag = row.select_one("td.list_title a")
        if not title_tag:
            continue

        href = title_tag.get("href", "")
        # job_id: URL의 쿼리스트링에서 추출
        job_id = ""
        if "GIJP_No=" in href:
            job_id = href.split("GIJP_No=")[-1].split("&")[0]
        elif "GI_No=" in href:
            job_id = href.split("GI_No=")[-1].split("&")[0]

        if not job_id:
            continue

        full_url = href if href.startswith("http") else GAMEJOB_BASE_URL + href

        postings.append({
            "job_id": job_id,
            "title": title_tag.get_text(strip=True),
            "company": cells[1].get_text(strip=True) if len(cells) > 1 else "",
            "career": cells[2].get_text(strip=True) if len(cells) > 2 else "",
            "location": cells[3].get_text(strip=True) if len(cells) > 3 else "",
            "deadline": cells[4].get_text(strip=True) if len(cells) > 4 else "",
            "url": full_url,
        })

    return postings


def _fetch_detail(url: str) -> tuple[str, list[str]]:
    """공고 상세 페이지에서 설명과 태그를 가져온다."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        resp.encoding = "euc-kr"
        soup = BeautifulSoup(resp.text, "lxml")

        desc_tag = soup.select_one("div.view_cont") or soup.select_one("div#contents")
        description = desc_tag.get_text(separator="\n", strip=True)[:3000] if desc_tag else ""

        tags = [t.get_text(strip=True) for t in soup.select("div.tag_area a")]

        return description, tags
    except requests.RequestException as e:
        logger.warning("상세 페이지 요청 실패 (%s): %s", url, e)
        return "", []


def crawl_jobs() -> list[JobPosting]:
    """gamejob.co.kr에서 채용공고를 크롤링해 반환한다."""
    all_postings: list[JobPosting] = []
    seen_ids: set[str] = set()

    for page in range(1, CRAWL_PAGES + 1):
        logger.info("페이지 %d/%d 크롤링 중...", page, CRAWL_PAGES)
        soup = _fetch_page(page)
        if not soup:
            continue

        raw_list = _parse_list_page(soup)
        if not raw_list:
            logger.info("페이지 %d에서 공고를 찾지 못했습니다.", page)
            break

        pre_filtered_in_page = 0
        for item in raw_list:
            if item["job_id"] in seen_ids:
                continue
            seen_ids.add(item["job_id"])

            if PREFILTER_BY_TITLE and not _passes_title_filter(item["title"]):
                pre_filtered_in_page += 1
                all_postings.append(JobPosting(
                    job_id=item["job_id"],
                    title=item["title"],
                    company=item["company"],
                    career=item["career"],
                    location=item["location"],
                    deadline=item["deadline"],
                    url=item["url"],
                    pre_filtered=True,
                ))
                continue

            time.sleep(REQUEST_DELAY)
            description, tags = _fetch_detail(item["url"])

            all_postings.append(JobPosting(
                job_id=item["job_id"],
                title=item["title"],
                company=item["company"],
                career=item["career"],
                location=item["location"],
                deadline=item["deadline"],
                url=item["url"],
                description=description,
                tags=tags,
            ))

        if pre_filtered_in_page:
            logger.info("페이지 %d: 제목 사전 필터로 %d개 제외", page, pre_filtered_in_page)

        time.sleep(REQUEST_DELAY)

    logger.info("총 %d개 공고 크롤링 완료", len(all_postings))
    return all_postings
