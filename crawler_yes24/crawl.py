#!/usr/bin/env python3
"""
Yes24 도서 독자 리뷰 크롤러 (한국)
한강 『채식주의자』 박사학위논문 보조 baseline 수집용

두 가지 사용법:
  1) GUI:    streamlit run app.py  (권장 — 일반인 친화)
  2) CLI:    python crawl.py 108422348 --max-pages 20

요구사항: Chrome 또는 Chromium 설치 필요.

⚠️ Yes24 페이지 셀렉터는 자료(web_scraping_tutorial.ipynb) 후보 기반.
   페이지 구조 변경 시 parse_reviews() 셀렉터 조정 필요.
"""

from __future__ import annotations

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
from typing import Callable

import pandas as pd
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

# === 상수 ===
DEFAULT_DELAY_MIN = 2.0
DEFAULT_DELAY_MAX = 5.0
RANDOM_SEED = 42
NOBEL_PIVOT_DATE = "2024-10-10"

KNOWN_PRODUCTS = {
    "vegetarian_kr_changbi": ("108422348", "한강 『채식주의자』 (창비)"),
}


# === 익명화 ===
def hash_user(user_id: str, salt: str) -> str:
    if not user_id:
        return ""
    return hashlib.sha256(f"{user_id}{salt}".encode("utf-8")).hexdigest()[:16]


def extract_product_id(url_or_id: str) -> str:
    s = str(url_or_id).strip()
    if s.isdigit():
        return s
    m = re.search(r"/Goods/(\d+)", s)
    if not m:
        raise ValueError(f"URL 또는 ID 형식이 아님: {url_or_id}")
    return m.group(1)


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


def is_post_nobel(date_str: str) -> bool:
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


def parse_reviews(html: str, salt: str) -> list[dict]:
    """
    Yes24 리뷰 영역 HTML → dict 리스트.
    셀렉터는 자료 §5의 후보를 다중 시도. 페이지 변경 시 조정 필요.
    """
    soup = BeautifulSoup(html, "lxml")

    candidates = [
        "div.reviewInfoGrp",
        "li.reviewInfoItem",
        "div.review_cont",
        "div.reviewInfoBot",
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
            user_elem = (item.select_one(".info_writer")
                         or item.select_one(".reviewWriter")
                         or item.select_one("a.name")
                         or item.select_one(".writer"))
            username = user_elem.get_text(strip=True) if user_elem else ""

            rating = None
            rating_elem = (item.select_one(".rating_grade")
                           or item.select_one(".cRating em")
                           or item.select_one(".rating em"))
            if rating_elem:
                m = re.search(r"\d+", rating_elem.get_text())
                if m:
                    rating = int(m.group())

            date_elem = (item.select_one(".info_date")
                         or item.select_one(".reviewDate")
                         or item.select_one(".date"))
            date = date_elem.get_text(strip=True) if date_elem else ""

            text_elem = (item.select_one(".review_cont")
                         or item.select_one(".reviewInfoBot")
                         or item.select_one(".cont")
                         or item)
            text = text_elem.get_text(strip=True) if text_elem else ""
            text = re.sub(r"\s+", " ", text)
            if len(text) < 5:
                continue

            helpful = 0
            helpful_elem = (item.select_one(".helpful_num")
                            or item.select_one(".cntHelpful"))
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


def go_to_review_tab(driver: webdriver.Chrome, wait: WebDriverWait,
                     log: Callable[[str], None]) -> bool:
    selectors = ["a[href*='#review']", "a#yesReviewTab", "a.reviewTab"]
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
    log("  리뷰 탭 셀렉터 미발견 — 기본 페이지에서 파싱 시도")
    return False


def click_next_page(driver: webdriver.Chrome, page_num: int,
                    log: Callable[[str], None]) -> bool:
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
    log(f"  다음 페이지 버튼 미발견 (p={page_num}) → 종료")
    return False


# ========================================================
# 🌟 핵심 재사용 함수
# ========================================================
def crawl_to_df(
    product_id: str,
    *,
    max_pages: int = 10,
    date_from: str | None = None,
    date_to: str | None = None,
    delay_min: float = DEFAULT_DELAY_MIN,
    delay_max: float = DEFAULT_DELAY_MAX,
    headless: bool = True,
    salt: str | None = None,
    out_dir: str | Path | None = None,
    progress_callback: Callable[[int, int, str], None] | None = None,
    log_callback: Callable[[str], None] | None = None,
) -> tuple[pd.DataFrame, dict]:
    """
    Yes24 리뷰 수집 본체.
    Returns: (df, meta)
    """
    if salt is None:
        load_dotenv()
        salt = os.environ.get("ANONYMIZATION_SALT", "")
    if not salt or salt.startswith("__REPLACE_ME__"):
        raise RuntimeError("ANONYMIZATION_SALT가 설정되지 않음 (.env 확인)")

    random.seed(RANDOM_SEED)

    log = log_callback or (lambda m: print(m))
    progress = progress_callback or (lambda c, t, m: None)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    save_files = out_dir is not None
    csv_path = log_path = snap_dir = None
    csv_writer = csv_file = file_logger = None

    if save_files:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        snap_dir = out_dir / "_snapshots" / product_id
        snap_dir.mkdir(parents=True, exist_ok=True)
        log_path = out_dir / f"yes24_{product_id}_{timestamp}.log"
        csv_path = out_dir / f"yes24_{product_id}_{timestamp}.csv"

        file_logger = logging.getLogger(f"yes24_{product_id}_{timestamp}")
        file_logger.setLevel(logging.INFO)
        h = logging.FileHandler(log_path, encoding="utf-8")
        h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        file_logger.addHandler(h)

        csv_file = csv_path.open("w", encoding="utf-8-sig", newline="")
        fieldnames = ["product_id", "user_id_hash", "rating", "date",
                      "helpful_votes", "is_post_nobel", "text",
                      "page", "crawl_timestamp"]
        csv_writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        csv_writer.writeheader()

    def _log(msg: str):
        log(msg)
        if file_logger:
            file_logger.info(msg)

    _log(f"=== Yes24 수집 시작: 상품 {product_id} ===")
    _log(f"설정: max_pages={max_pages}, date={date_from}~{date_to}, "
         f"headless={headless}")

    rows_all: list[dict] = []
    aborted = False
    driver = None

    try:
        progress(0, max_pages, "Chrome 드라이버 초기화 중…")
        driver = make_driver(headless=headless)
        wait = WebDriverWait(driver, 10)

        url = f"https://www.yes24.com/Product/Goods/{product_id}"
        _log(f"페이지 진입: {url}")
        driver.get(url)
        time.sleep(3)

        go_to_review_tab(driver, wait, _log)

        for page_idx in range(max_pages):
            page_num = page_idx + 1
            progress(page_idx, max_pages, f"페이지 {page_num}/{max_pages} 수집 중…")
            _log(f"[페이지 {page_num}/{max_pages}]")

            html = driver.page_source
            if save_files:
                (snap_dir / f"page_{page_num:03d}.html").write_text(
                    html, encoding="utf-8"
                )

            rows = parse_reviews(html, salt)
            _log(f"  파싱 {len(rows)}건")

            for row in rows:
                if not in_date_range(row["date"], date_from, date_to):
                    continue
                row["product_id"] = product_id
                row["page"] = page_num
                row["crawl_timestamp"] = datetime.now(timezone.utc).isoformat()
                rows_all.append(row)
                if csv_writer:
                    csv_writer.writerow(row)
            if csv_file:
                csv_file.flush()

            if page_idx >= max_pages - 1:
                break

            if not click_next_page(driver, page_num + 1, _log):
                break

            delay = random.uniform(delay_min, delay_max)
            _log(f"  ⏳ {delay:.1f}초 대기")
            time.sleep(delay)

    except WebDriverException as e:
        aborted = True
        _log(f"드라이버 오류: {e}")
    finally:
        if driver:
            driver.quit()
            _log("드라이버 종료")

    progress(max_pages, max_pages, f"완료 — 총 {len(rows_all)}건")
    _log(f"=== 수집 종료 — 총 {len(rows_all)}건 ===")

    if csv_file:
        csv_file.close()
    if file_logger:
        for h in file_logger.handlers[:]:
            h.close()
            file_logger.removeHandler(h)

    df = pd.DataFrame(rows_all)
    meta = {
        "csv_path": str(csv_path) if csv_path else None,
        "log_path": str(log_path) if log_path else None,
        "snap_dir": str(snap_dir) if snap_dir else None,
        "n_collected": len(rows_all),
        "aborted": aborted,
        "product_id": product_id,
    }
    return df, meta


# ========================================================
# CLI
# ========================================================
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Yes24 리뷰 크롤러 (CLI). GUI는 streamlit run app.py 사용.",
    )
    target = p.add_mutually_exclusive_group(required=True)
    target.add_argument("product_id", nargs="?")
    target.add_argument("--url")
    p.add_argument("--max-pages", type=int, default=10)
    p.add_argument("--date-from", default=None)
    p.add_argument("--date-to", default=None)
    p.add_argument("--out-dir", default="data")
    p.add_argument("--no-headless", action="store_true")
    p.add_argument("--delay-min", type=float, default=DEFAULT_DELAY_MIN)
    p.add_argument("--delay-max", type=float, default=DEFAULT_DELAY_MAX)
    return p.parse_args()


def main():
    args = parse_args()
    pid = extract_product_id(args.product_id or args.url)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    df, meta = crawl_to_df(
        pid,
        max_pages=args.max_pages,
        date_from=args.date_from,
        date_to=args.date_to,
        delay_min=args.delay_min,
        delay_max=args.delay_max,
        headless=not args.no_headless,
        out_dir=args.out_dir,
        log_callback=lambda m: None,
    )
    print(f"\n총 수집: {meta['n_collected']}건")
    print(f"CSV: {meta['csv_path']}")


if __name__ == "__main__":
    main()
