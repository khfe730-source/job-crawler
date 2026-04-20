import time
import logging
import requests
from bs4 import BeautifulSoup
from dataclasses import dataclass, field
from typing import Optional
from config import (
    GAMEJOB_BASE_URL,
    CRAWL_PAGES,
    REQUEST_DELAY,
    TARGET_JOBS,
)

logger = logging.getLogger(__name__)

GAMEJOB_SEARCH_URL = f"{GAMEJOB_BASE_URL}/Recruit/joblist"
GAMEJOB_PAGE_URL = f"{GAMEJOB_BASE_URL}/recruit/_GI_Job_List"

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


def _parse_job_rows(soup: BeautifulSoup) -> list[dict]:
    """페이지에서 채용공고 행들을 파싱한다."""
    postings = []
    seen_in_page: set[str] = set()

    for a_tag in soup.find_all("a", href=lambda h: h and "GI_No=" in h):
        href = a_tag.get("href", "")
        job_id = href.split("GI_No=")[-1].split("&")[0]
        if not job_id or job_id in seen_in_page:
            continue
        seen_in_page.add(job_id)

        full_url = href if href.startswith("http") else GAMEJOB_BASE_URL + href
        title = a_tag.get_text(strip=True)
        if not title:
            continue

        row = a_tag.find_parent("tr")
        if not row:
            continue

        cells = row.select("td")
        company = cells[0].get_text(strip=True) if cells else ""
        career_loc = cells[2].get_text(strip=True) if len(cells) > 2 else ""
        deadline = cells[-1].get_text(strip=True) if cells else ""

        postings.append({
            "job_id": job_id,
            "title": title,
            "company": company,
            "career": career_loc,
            "location": "",
            "deadline": deadline,
            "url": full_url,
        })

    return postings


def _fetch_detail(url: str) -> tuple[str, list[str]]:
    """공고 상세 페이지에서 설명과 태그를 가져온다."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        if not resp.encoding or resp.encoding.lower() == "iso-8859-1":
            resp.encoding = resp.apparent_encoding
        soup = BeautifulSoup(resp.text, "lxml")

        desc_tag = (
            soup.select_one("div.view_cont")
            or soup.select_one("div.recruit_view")
            or soup.select_one("div#contents")
        )
        description = desc_tag.get_text(separator="\n", strip=True)[:3000] if desc_tag else ""

        tags = [t.get_text(strip=True) for t in soup.select("div.tag_area a")]

        return description, tags
    except requests.RequestException as e:
        logger.warning("상세 페이지 요청 실패 (%s): %s", url, e)
        return "", []


def _crawl_keyword(keyword: str) -> list[dict]:
    """단일 키워드로 gamejob 검색 결과를 수집한다. 세션으로 페이지네이션 유지."""
    session = requests.Session()
    session.headers.update(HEADERS)
    items: list[dict] = []

    for page in range(1, CRAWL_PAGES + 1):
        try:
            if page == 1:
                resp = session.get(
                    GAMEJOB_SEARCH_URL,
                    params={
                        "menucode": "searchtot",
                        "searchtype": "all",
                        "searchstring": keyword,
                    },
                    timeout=15,
                )
            else:
                resp = session.get(
                    GAMEJOB_PAGE_URL,
                    params={"Page": page},
                    timeout=15,
                )

            resp.raise_for_status()
            if not resp.encoding or resp.encoding.lower() == "iso-8859-1":
                resp.encoding = resp.apparent_encoding
            soup = BeautifulSoup(resp.text, "lxml")

            page_items = _parse_job_rows(soup)
            if not page_items:
                logger.info("'%s' 검색: 페이지 %d 공고 없음, 중단", keyword, page)
                break

            items.extend(page_items)
            logger.info("'%s' 검색: 페이지 %d에서 %d개 수집", keyword, page, len(page_items))

            if page < CRAWL_PAGES:
                time.sleep(REQUEST_DELAY)

        except requests.RequestException as e:
            logger.error("'%s' 검색 페이지 %d 요청 실패: %s", keyword, page, e)
            break

    return items


def crawl_jobs() -> list[JobPosting]:
    """TARGET_JOBS 키워드별로 gamejob을 검색해 채용공고를 반환한다."""
    seen_ids: set[str] = set()
    all_postings: list[JobPosting] = []

    for keyword in TARGET_JOBS:
        logger.info("=== '%s' 키워드 검색 시작 ===", keyword)
        raw_items = _crawl_keyword(keyword)

        new_in_keyword = 0
        for item in raw_items:
            if item["job_id"] in seen_ids:
                continue
            seen_ids.add(item["job_id"])
            new_in_keyword += 1

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

        logger.info("'%s' 검색 완료: 신규 %d개 (중복 제외 후)", keyword, new_in_keyword)
        time.sleep(REQUEST_DELAY)

    logger.info("총 %d개 공고 수집 완료", len(all_postings))
    return all_postings
