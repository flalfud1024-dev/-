#!/usr/bin/env python3
"""
豆瓣 도서 독자 단평(短评) 크롤러
한강 『채식주의자』 박사학위논문 데이터 수집용

두 가지 사용법:
  1) GUI:    streamlit run app.py  (권장 — 일반인 친화)
  2) CLI:    python crawl.py 35534519 --max-pages 20

논문 인용: 본 크롤러로 수집된 데이터는 본 저장소 commit hash로 재현 가능.
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
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# === 상수 ===
DEFAULT_DELAY_MIN = 3.0
DEFAULT_DELAY_MAX = 6.0
DEFAULT_TIMEOUT = 10
DEFAULT_MAX_RETRIES = 3
RANDOM_SEED = 42
NOBEL_PIVOT_DATE = "2024-10-10"  # 한강 노벨문학상 발표일 (결정 D3: 분리 분석)

HEADERS_BASE = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,ko;q=0.7",
    "Referer": "https://book.douban.com/",
}

# 본 학위논문 사전 등록 도서
KNOWN_BOOKS = {
    "huchutong_2021": ("35534519", "후추통 2021 (간체)"),
    "taiwan_2016":    ("26735623", "천일 2016 (번체, 타이완)"),
    "tianyi_2013":    ("24847418", "천일 2013 (간체, 본토)"),
}


# === 익명화 ===
def hash_user(user_id: str, salt: str) -> str:
    if not user_id:
        return ""
    return hashlib.sha256(f"{user_id}{salt}".encode("utf-8")).hexdigest()[:16]


# === Nobel 전후 판별 (결정 D3) ===
def is_post_nobel(date_str: str) -> bool:
    """2024-10-10(한강 노벨상 발표일) 이후 작성 여부"""
    if not date_str:
        return False
    m = re.match(r"(\d{4}-\d{2}-\d{2})", str(date_str))
    return bool(m) and m.group(1) >= NOBEL_PIVOT_DATE


# === ID 추출 (URL 또는 ID 모두 허용) ===
def extract_book_id(url_or_id: str) -> str:
    s = str(url_or_id).strip()
    if s.isdigit():
        return s
    m = re.search(r"/subject/(\d+)", s)
    if not m:
        raise ValueError(f"URL 또는 ID 형식이 아님: {url_or_id}")
    return m.group(1)


# === 페이지 가져오기 ===
def fetch_page(session: requests.Session, url: str,
               log: Callable[[str], None],
               max_retries: int = DEFAULT_MAX_RETRIES) -> str | None:
    for attempt in range(1, max_retries + 1):
        try:
            r = session.get(url, timeout=DEFAULT_TIMEOUT)
            if r.status_code == 200:
                return r.text
            log(f"  HTTP {r.status_code} (시도 {attempt}/{max_retries})")
            if r.status_code == 403:
                if attempt == max_retries:
                    log("  ⛔ 403 누적 — IP 차단으로 판단, 수집 중단")
                    return None
                time.sleep(5 * attempt)
        except requests.RequestException as e:
            log(f"  요청 실패: {e} (시도 {attempt}/{max_retries})")
            time.sleep(3 * attempt)
    return None


# === 단평 파싱 ===
def parse_comments(html: str, salt: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    items = soup.select("li.comment-item")
    out = []
    for item in items:
        try:
            user_elem = item.select_one("span.comment-info a")
            username_raw = user_elem.get_text(strip=True) if user_elem else ""

            rating = None
            rating_elem = item.select_one(
                'span.comment-info span[class*="rating"]'
            )
            if rating_elem:
                for c in rating_elem.get("class", []):
                    if c.startswith("allstar"):
                        try:
                            rating = int(c.replace("allstar", "")) // 10
                        except ValueError:
                            pass
                        break

            date_elem = item.select_one("span.comment-info span.comment-time")
            date = date_elem.get_text(strip=True) if date_elem else ""

            content_elem = item.select_one("span.short")
            text = content_elem.get_text(strip=True) if content_elem else ""
            if not text:
                continue

            votes_elem = item.select_one("span.vote-count")
            try:
                votes = int(votes_elem.get_text(strip=True)) if votes_elem else 0
            except ValueError:
                votes = 0

            out.append({
                "review_id": item.get("data-cid", "") or "",
                "user_id_hash": hash_user(username_raw, salt),
                "rating": rating,
                "date": date,
                "likes": votes,
                "is_post_nobel": is_post_nobel(date),
                "text": text,
            })
        except Exception:
            continue
    return out


def in_date_range(date_str: str, date_from: str | None,
                  date_to: str | None) -> bool:
    if not date_str:
        return True
    m = re.match(r"(\d{4}-\d{2}-\d{2})", date_str)
    if not m:
        return True
    d = m.group(1)
    if date_from and d < date_from:
        return False
    if date_to and d > date_to:
        return False
    return True


# ========================================================
# 🌟 핵심 재사용 함수: GUI/CLI 공용
# ========================================================
def crawl_to_df(
    book_id: str,
    *,
    max_pages: int = 10,
    sort: str = "score",
    status: str = "P",
    date_from: str | None = None,
    date_to: str | None = None,
    delay_min: float = DEFAULT_DELAY_MIN,
    delay_max: float = DEFAULT_DELAY_MAX,
    salt: str | None = None,
    out_dir: str | Path | None = None,
    progress_callback: Callable[[int, int, str], None] | None = None,
    log_callback: Callable[[str], None] | None = None,
) -> tuple[pd.DataFrame, dict]:
    """
    豆瓣 단평 수집 본체 함수.

    Args:
        book_id: 豆瓣 도서 ID (숫자 문자열)
        max_pages: 최대 페이지 (페이지당 20건)
        sort: 'score' | 'new' | 'time'
        status: 'P' | 'F' | 'W'
        date_from / date_to: YYYY-MM-DD 형식 필터 (선택)
        salt: 익명화 salt (None이면 환경변수에서 로드)
        out_dir: 지정 시 CSV/로그/스냅샷 저장. None이면 메모리만.
        progress_callback(current, total, msg): GUI 진행률 갱신용
        log_callback(msg): GUI 로그 영역 갱신용

    Returns:
        (df, meta) — df는 수집 결과 DataFrame,
                    meta는 {csv_path, log_path, snap_dir, n_collected, aborted}
    """
    if salt is None:
        load_dotenv()
        salt = os.environ.get("ANONYMIZATION_SALT", "")
    if not salt or salt.startswith("__REPLACE_ME__"):
        raise RuntimeError("ANONYMIZATION_SALT가 설정되지 않음 (.env 확인)")

    random.seed(RANDOM_SEED)

    # 콜백 기본값
    log = log_callback or (lambda m: print(m))
    progress = progress_callback or (lambda c, t, m: None)

    # 출력 디렉토리
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    save_files = out_dir is not None
    csv_path = log_path = snap_dir = None
    csv_writer = csv_file = None
    file_logger = None

    if save_files:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        snap_dir = out_dir / "_snapshots" / book_id
        snap_dir.mkdir(parents=True, exist_ok=True)
        log_path = out_dir / f"douban_{book_id}_{timestamp}.log"
        csv_path = out_dir / f"douban_{book_id}_{timestamp}.csv"

        file_logger = logging.getLogger(f"douban_{book_id}_{timestamp}")
        file_logger.setLevel(logging.INFO)
        h = logging.FileHandler(log_path, encoding="utf-8")
        h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        file_logger.addHandler(h)

        csv_file = csv_path.open("w", encoding="utf-8-sig", newline="")
        fieldnames = ["review_id", "book_id", "user_id_hash", "rating",
                      "date", "likes", "is_post_nobel", "text",
                      "page", "crawl_timestamp"]
        csv_writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        csv_writer.writeheader()

    def _log(msg: str):
        log(msg)
        if file_logger:
            file_logger.info(msg)

    _log(f"=== 豆瓣 수집 시작: 도서 {book_id} ===")
    _log(f"설정: max_pages={max_pages}, sort={sort}, status={status}, "
         f"date={date_from}~{date_to}")

    session = requests.Session()
    headers = dict(HEADERS_BASE)
    contact = os.environ.get("RESEARCHER_EMAIL", "")
    if contact:
        headers["From"] = contact
    session.headers.update(headers)

    rows_all: list[dict] = []
    aborted = False

    for page_idx in range(max_pages):
        start = page_idx * 20
        url = (f"https://book.douban.com/subject/{book_id}/comments/"
               f"?start={start}&limit=20&status={status}&sort={sort}")
        progress(page_idx, max_pages, f"페이지 {page_idx+1}/{max_pages} 수집 중…")
        _log(f"[페이지 {page_idx+1}/{max_pages}] {url}")

        html = fetch_page(session, url, _log)
        if html is None:
            aborted = True
            _log(f"수집 중단 — 페이지 {page_idx+1}에서 차단")
            break

        if save_files:
            (snap_dir / f"page_{page_idx+1:03d}.html").write_text(
                html, encoding="utf-8"
            )

        rows = parse_comments(html, salt)
        if not rows:
            _log("  단평 없음 → 종료")
            break

        for row in rows:
            if not in_date_range(row["date"], date_from, date_to):
                continue
            row["book_id"] = book_id
            row["page"] = page_idx + 1
            row["crawl_timestamp"] = datetime.now(timezone.utc).isoformat()
            rows_all.append(row)
            if csv_writer:
                csv_writer.writerow(row)

        _log(f"  ✓ 파싱 {len(rows)}건, 누적 {len(rows_all)}건")
        if csv_file:
            csv_file.flush()

        if page_idx < max_pages - 1:
            delay = random.uniform(delay_min, delay_max)
            _log(f"  ⏳ {delay:.1f}초 대기")
            time.sleep(delay)

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
        "book_id": book_id,
    }
    return df, meta


# ========================================================
# CLI
# ========================================================
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="豆瓣 단평 크롤러 (CLI). GUI는 streamlit run app.py 사용.",
    )
    target = p.add_mutually_exclusive_group(required=True)
    target.add_argument("book_id", nargs="?", help="豆瓣 도서 ID")
    target.add_argument("--url", help="豆瓣 도서 페이지 URL")

    p.add_argument("--max-pages", type=int, default=10)
    p.add_argument("--sort", choices=["score", "new", "time"], default="score")
    p.add_argument("--status", choices=["P", "F", "W"], default="P")
    p.add_argument("--date-from", default=None)
    p.add_argument("--date-to", default=None)
    p.add_argument("--out-dir", default="data")
    p.add_argument("--delay-min", type=float, default=DEFAULT_DELAY_MIN)
    p.add_argument("--delay-max", type=float, default=DEFAULT_DELAY_MAX)
    return p.parse_args()


def main():
    args = parse_args()
    book_id = extract_book_id(args.book_id or args.url)

    # CLI: stdout 로깅
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    df, meta = crawl_to_df(
        book_id,
        max_pages=args.max_pages,
        sort=args.sort,
        status=args.status,
        date_from=args.date_from,
        date_to=args.date_to,
        delay_min=args.delay_min,
        delay_max=args.delay_max,
        out_dir=args.out_dir,
        log_callback=lambda m: None,  # logging.basicConfig가 처리
    )
    print(f"\n총 수집: {meta['n_collected']}건")
    print(f"CSV: {meta['csv_path']}")
    print(f"로그: {meta['log_path']}")


if __name__ == "__main__":
    main()
