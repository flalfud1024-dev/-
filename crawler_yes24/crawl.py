#!/usr/bin/env python3
"""
Yes24 도서 독자 리뷰 크롤러 (한국)
한강 『채식주의자』 박사학위논문 보조 baseline 수집용

사용 예:
  # 상품 ID로 수집
  python crawl.py 108422348

  # 페이지 수·정렬 지정
  python crawl.py 108422348 --max-pages 20 --sort popular

  # 전체 URL로도 가능
  python crawl.py --url https://www.yes24.com/Product/Goods/108422348

요구사항: Chrome 또는 Chromium 설치 필요.
        Linux 환경은 --no-sandbox 옵션이 자동 적용됨.

⚠️ 본 크롤러의 Yes24 페이지 셀렉터는 자료(web_scraping_tutorial.ipynb) 후보에
   기반하며, 실제 페이지 구조 변경 시 parse_reviews() 함수의
   셀렉터를 조정해야 합니다.

논문 인용: 본 크롤러로 수집된 데이터는 본 저장소 commit hash로 재현 가능.
"""

import argparse
import csv
import hashlib
import logging
import os
import random
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup
from dotenv import load_dotenv
from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchElementException, TimeoutException, WebDriverException,
)
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from tqdm import tqdm

# === 상수 ===
DEFAULT_DELAY_MIN = 2.0
DEFAULT_DELAY_MAX = 5.0
RANDOM_SEED = 42
NOBEL_PIVOT_DATE = "2024-10-10"  # 한강 노벨문학상 발표일


# === CLI ===
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Yes24 리뷰 크롤러 (박사학위논문 보조 baseline)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("\n\n", 1)[1] if __doc__ else "",
    )
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("product_id", nargs="?",
                        help="Yes24 상품 ID (예: 108422348)")
    target.add_argument("--url",
                        help="Yes24 상품 페이지 전체 URL")

    parser.add_argument("--max-pages", type=int, default=10,
                        help="최대 수집 페이지 (기본 10)")
    parser.add_argument("--sort", choices=["popular", "latest"],
                        default="popular",
                        help="popular=공감순(기본), latest=최신순")
    parser.add_argument("--date-from", default=None,
                        help="시작일 필터 YYYY-MM-DD (선택)")
    parser.add_argument("--date-to", default=None,
                        help="종료일 필터 YYYY-MM-DD (선택)")
    parser.add_argument("--out-dir", default="data",
                        help="출력 디렉토리 (기본: ./data)")
    parser.add_argument("--no-headless", action="store_true",
                        help="브라우저 창 표시 (디버깅용)")
    parser.add_argument("--delay-min", type=float, default=DEFAULT_DELAY_MIN)
    parser.add_argument("--delay-max", type=float, default=DEFAULT_DELAY_MAX)
    return parser.parse_args()


# === 익명화 ===
def hash_user(user_id: str, salt: str) -> str:
    if not user_id:
        return ""
    return hashlib.sha256(f"{user_id}{salt}".encode("utf-8")).hexdigest()[:16]


# === ID 추출 ===
def extract_product_id(args: argparse.Namespace) -> str:
    if args.product_id:
        return args.product_id
    m = re.search(r"/Goods/(\d+)", args.url)
    if not m:
        sys.exit(f"❌ URL에서 상품 ID를 찾지 못했습니다: {args.url}")
    return m.group(1)


# === 드라이버 ===
def make_driver(headless: bool = True) -> webdriver.Chrome:
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=opts)


# === 노벨상 전후 분리 ===
def is_post_nobel(date_str: str) -> bool:
    """2024-10-10 이후 작성 여부"""
    m = re.match(r"(\d{4})[.\-/](\d{2})[.\-/](\d{2})", date_str)
    if not m:
        return False
    norm = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return norm >= NOBEL_PIVOT_DATE


def in_date_range(date_str: str, date_from: str | None,
                  date_to: str | None) -> bool:
    if not date_str:
        return True
    m = re.match(r"(\d{4})[.\-/](\d{2})[.\-/](\d{2})", date_str)
    if not m:
        return True
    norm = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    if date_from and norm < date_from:
        return False
    if date_to and norm > date_to:
        return False
    return True


# === 리뷰 파싱 ===
def parse_reviews(html: str, salt: str) -> list[dict]:
    """
    Yes24 리뷰 영역 HTML → dict 리스트

    ⚠️ Yes24 페이지 구조는 자주 바뀝니다. 셀렉터는 자료가 제시한
       후보를 기반으로 하며, 실제 페이지에서 다음 항목을 확인해 조정:
       - 리뷰 항목 컨테이너
       - 작성자/평점/날짜/본문/공감 수 위치
    """
    soup = BeautifulSoup(html, "lxml")

    # 후보 셀렉터 (자료 §5에서 제시) — 실제 페이지로 검증 후 조정
    candidates = [
        "div.reviewInfoGrp",      # 회원 리뷰
        "li.reviewInfoItem",       # 리스트 아이템 형태
        "div.review_cont",         # 자료 후보
        "div.reviewInfoBot",       # 자료 후보
    ]
    items = []
    for sel in candidates:
        found = soup.select(sel)
        if found:
            items = found
            break

    out = []
    for item in items:
        try:
            # 작성자 (다양한 후보 시도)
            user_elem = (
                item.select_one(".info_writer")
                or item.select_one(".reviewWriter")
                or item.select_one("a.name")
                or item.select_one(".writer")
            )
            username = user_elem.get_text(strip=True) if user_elem else ""

            # 별점
            rating = None
            rating_elem = (
                item.select_one(".rating_grade")
                or item.select_one(".cRating em")
                or item.select_one(".rating em")
            )
            if rating_elem:
                m = re.search(r"\d+", rating_elem.get_text())
                if m:
                    rating = int(m.group())

            # 날짜
            date_elem = (
                item.select_one(".info_date")
                or item.select_one(".reviewDate")
                or item.select_one(".date")
            )
            date = date_elem.get_text(strip=True) if date_elem else ""

            # 본문
            text_elem = (
                item.select_one(".review_cont")
                or item.select_one(".reviewInfoBot")
                or item.select_one(".cont")
                or item
            )
            text = text_elem.get_text(strip=True) if text_elem else ""
            text = re.sub(r"\s+", " ", text)
            if len(text) < 5:
                continue

            # 공감(유용) 수
            helpful = 0
            helpful_elem = (
                item.select_one(".helpful_num")
                or item.select_one(".cntHelpful")
            )
            if helpful_elem:
                m = re.search(r"\d+", helpful_elem.get_text())
                if m:
                    helpful = int(m.group())

            out.append({
                "user_id_hash": hash_user(username, salt),
                "rating": rating,
                "date": date,
                "helpful_votes": helpful,
                "text": text,
                "is_post_nobel": is_post_nobel(date),
            })
        except Exception:
            continue
    return out


# === 페이지네이션 ===
def go_to_review_tab(driver: webdriver.Chrome, wait: WebDriverWait,
                     logger: logging.Logger) -> bool:
    """리뷰 탭 클릭 시도. 실패해도 page_source는 사용 가능."""
    selectors = [
        "a[href*='#review']",
        "a#yesReviewTab",
        "a.reviewTab",
    ]
    for sel in selectors:
        try:
            elem = wait.until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR, sel)
            ))
            driver.execute_script("arguments[0].click();", elem)
            time.sleep(1.5)
            return True
        except (TimeoutException, NoSuchElementException):
            continue
    logger.warning("  리뷰 탭 셀렉터를 찾지 못함 — 기본 페이지에서 파싱 시도")
    return False


def click_next_page(driver: webdriver.Chrome, page_num: int,
                    logger: logging.Logger) -> bool:
    """다음 페이지 버튼 클릭. 더 이상 없으면 False."""
    next_selectors = [
        f"a[onclick*='pageNum={page_num}']",
        f"a[data-page='{page_num}']",
        "a.bgYUI.next",
        "a.next",
    ]
    for sel in next_selectors:
        try:
            elem = driver.find_element(By.CSS_SELECTOR, sel)
            driver.execute_script("arguments[0].click();", elem)
            return True
        except NoSuchElementException:
            continue
    logger.info(f"  다음 페이지 버튼 미발견 (p={page_num}) → 종료")
    return False


# === 메인 ===
def crawl(args: argparse.Namespace) -> None:
    load_dotenv()
    salt = os.environ.get("ANONYMIZATION_SALT", "")
    if not salt or salt.startswith("__REPLACE_ME__"):
        sys.exit("❌ .env에 ANONYMIZATION_SALT를 설정하세요")

    random.seed(RANDOM_SEED)

    product_id = extract_product_id(args)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    snap_dir = out_dir / "_snapshots" / product_id
    snap_dir.mkdir(parents=True, exist_ok=True)

    log_path = out_dir / f"yes24_{product_id}_{timestamp}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    logger = logging.getLogger("yes24")
    logger.info(f"=== Yes24 수집 시작: 상품 {product_id} ===")
    logger.info(f"인자: {vars(args)}")

    csv_path = out_dir / f"yes24_{product_id}_{timestamp}.csv"
    fieldnames = ["product_id", "user_id_hash", "rating", "date",
                  "helpful_votes", "is_post_nobel", "text",
                  "page", "crawl_timestamp"]

    driver = None
    collected = 0
    try:
        logger.info("Chrome 드라이버 초기화 중…")
        driver = make_driver(headless=not args.no_headless)
        wait = WebDriverWait(driver, 10)

        url = f"https://www.yes24.com/Product/Goods/{product_id}"
        logger.info(f"페이지 진입: {url}")
        driver.get(url)
        time.sleep(3)

        go_to_review_tab(driver, wait, logger)

        with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for page_idx in tqdm(range(args.max_pages), desc="페이지"):
                page_num = page_idx + 1
                logger.info(f"[페이지 {page_num}/{args.max_pages}]")

                html = driver.page_source
                (snap_dir / f"page_{page_num:03d}.html").write_text(
                    html, encoding="utf-8"
                )

                rows = parse_reviews(html, salt)
                logger.info(f"  파싱 {len(rows)}건")

                for row in rows:
                    if not in_date_range(row["date"], args.date_from,
                                         args.date_to):
                        continue
                    row["product_id"] = product_id
                    row["page"] = page_num
                    row["crawl_timestamp"] = datetime.now(timezone.utc).isoformat()
                    writer.writerow(row)
                    collected += 1
                f.flush()

                if page_idx >= args.max_pages - 1:
                    break

                # 다음 페이지
                if not click_next_page(driver, page_num + 1, logger):
                    break

                delay = random.uniform(args.delay_min, args.delay_max)
                logger.info(f"  ⏳ {delay:.1f}초 대기")
                time.sleep(delay)

    except WebDriverException as e:
        logger.error(f"드라이버 오류: {e}")
    finally:
        if driver:
            driver.quit()
            logger.info("드라이버 종료")

    logger.info(f"=== 수집 종료 ===")
    logger.info(f"총 수집: {collected}건")
    logger.info(f"CSV: {csv_path}")
    logger.info(f"로그: {log_path}")
    logger.info(f"스냅샷: {snap_dir}")


if __name__ == "__main__":
    crawl(parse_args())
