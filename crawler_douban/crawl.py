#!/usr/bin/env python3
"""
豆瓣 도서 독자 단평(短评) 크롤러
한강 『채식주의자』 박사학위논문 데이터 수집용

사용 예:
  # 도서 ID로 수집 (가장 일반적)
  python crawl.py 35534519

  # 페이지 수 지정
  python crawl.py 35534519 --max-pages 20

  # 정렬: 공감순(score) 또는 시간순(new)
  python crawl.py 35534519 --sort score

  # 날짜 필터 (수집 후 후처리)
  python crawl.py 35534519 --date-from 2024-01-01 --date-to 2024-12-31

  # 전체 URL로도 수집 가능
  python crawl.py --url https://book.douban.com/subject/35534519/

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

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from tqdm import tqdm

# === 상수 ===
SCRIPT_DIR = Path(__file__).parent
DEFAULT_DELAY_MIN = 3.0
DEFAULT_DELAY_MAX = 6.0
DEFAULT_TIMEOUT = 10
DEFAULT_MAX_RETRIES = 3
RANDOM_SEED = 42  # 재현성

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


# === CLI ===
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="豆瓣 단평 크롤러 (박사학위논문 데이터 수집용)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("\n\n", 1)[1] if __doc__ else "",
    )
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("book_id", nargs="?",
                        help="豆瓣 도서 ID (예: 35534519)")
    target.add_argument("--url",
                        help="豆瓣 도서 페이지 전체 URL")

    parser.add_argument("--max-pages", type=int, default=10,
                        help="최대 수집 페이지 (페이지당 20건, 기본 10)")
    parser.add_argument("--sort", choices=["score", "new", "time"],
                        default="score",
                        help="정렬: score=공감순(기본), new/time=시간순")
    parser.add_argument("--status", choices=["P", "F", "W"], default="P",
                        help="P=읽음(기본), F=읽는중, W=읽고싶음")
    parser.add_argument("--date-from", default=None,
                        help="시작일 필터 YYYY-MM-DD (선택)")
    parser.add_argument("--date-to", default=None,
                        help="종료일 필터 YYYY-MM-DD (선택)")
    parser.add_argument("--out-dir", default="data",
                        help="출력 디렉토리 (기본: ./data)")
    parser.add_argument("--delay-min", type=float, default=DEFAULT_DELAY_MIN)
    parser.add_argument("--delay-max", type=float, default=DEFAULT_DELAY_MAX)
    return parser.parse_args()


# === 익명화 ===
def hash_user(user_id: str, salt: str) -> str:
    """SHA-256(user_id + salt) — 사용자 식별자 익명화"""
    if not user_id:
        return ""
    return hashlib.sha256(f"{user_id}{salt}".encode("utf-8")).hexdigest()[:16]


# === ID 추출 ===
def extract_book_id(args: argparse.Namespace) -> str:
    if args.book_id:
        return args.book_id
    m = re.search(r"/subject/(\d+)", args.url)
    if not m:
        sys.exit(f"❌ URL에서 도서 ID를 찾지 못했습니다: {args.url}")
    return m.group(1)


# === 페이지 가져오기 ===
def fetch_page(session: requests.Session, url: str,
               logger: logging.Logger,
               max_retries: int = DEFAULT_MAX_RETRIES) -> str | None:
    """403 발생 시 재시도 후 즉시 중단 신호 반환(None)"""
    for attempt in range(1, max_retries + 1):
        try:
            r = session.get(url, timeout=DEFAULT_TIMEOUT)
            if r.status_code == 200:
                return r.text
            logger.warning(f"  HTTP {r.status_code} (attempt {attempt}/{max_retries})")
            if r.status_code == 403:
                if attempt == max_retries:
                    logger.error("  403 누적 — IP 차단으로 판단, 수집 중단")
                    return None
                time.sleep(5 * attempt)  # 지수 백오프
        except requests.RequestException as e:
            logger.warning(f"  요청 실패: {e} (attempt {attempt}/{max_retries})")
            time.sleep(3 * attempt)
    return None


# === 단평 파싱 ===
def parse_comments(html: str, salt: str) -> list[dict]:
    """豆瓣 단평 페이지 HTML → 리뷰 dict 리스트"""
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
            votes_raw = votes_elem.get_text(strip=True) if votes_elem else "0"
            try:
                votes = int(votes_raw)
            except ValueError:
                votes = 0

            review_id = item.get("data-cid", "") or ""

            out.append({
                "review_id": review_id,
                "user_id_hash": hash_user(username_raw, salt),
                "rating": rating,
                "date": date,
                "likes": votes,
                "text": text,
            })
        except Exception as e:
            # 개별 항목 실패는 전체 수집을 막지 않음
            continue
    return out


# === 날짜 필터 ===
def in_date_range(date_str: str, date_from: str | None,
                  date_to: str | None) -> bool:
    if not date_str:
        return True  # 날짜 없는 리뷰는 보존
    # 豆瓣 날짜: "2024-03-15" 형식 가정
    m = re.match(r"(\d{4}-\d{2}-\d{2})", date_str)
    if not m:
        return True
    d = m.group(1)
    if date_from and d < date_from:
        return False
    if date_to and d > date_to:
        return False
    return True


# === 메인 ===
def crawl(args: argparse.Namespace) -> None:
    load_dotenv()
    salt = os.environ.get("ANONYMIZATION_SALT", "")
    if not salt or salt.startswith("__REPLACE_ME__"):
        sys.exit("❌ .env에 ANONYMIZATION_SALT를 설정하세요 "
                 "(.env.example 참고)")

    random.seed(RANDOM_SEED)  # 재현성: 지연 패턴 고정

    book_id = extract_book_id(args)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    snap_dir = out_dir / "_snapshots" / book_id
    snap_dir.mkdir(parents=True, exist_ok=True)

    # 로깅
    log_path = out_dir / f"douban_{book_id}_{timestamp}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    logger = logging.getLogger("douban")
    logger.info(f"=== 豆瓣 수집 시작: 도서 {book_id} ===")
    logger.info(f"인자: {vars(args)}")

    # 세션
    session = requests.Session()
    headers = dict(HEADERS_BASE)
    contact = os.environ.get("RESEARCHER_EMAIL", "")
    if contact:
        headers["From"] = contact  # 학술 목적 명시
    session.headers.update(headers)

    csv_path = out_dir / f"douban_{book_id}_{timestamp}.csv"
    fieldnames = ["review_id", "book_id", "user_id_hash", "rating",
                  "date", "likes", "text", "page", "crawl_timestamp"]

    collected = 0
    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for page_idx in tqdm(range(args.max_pages), desc="페이지"):
            start = page_idx * 20
            url = (
                f"https://book.douban.com/subject/{book_id}/comments/"
                f"?start={start}&limit=20&status={args.status}"
                f"&sort={args.sort}"
            )
            logger.info(f"[페이지 {page_idx+1}/{args.max_pages}] {url}")

            html = fetch_page(session, url, logger)
            if html is None:
                logger.error(f"수집 중단 — 페이지 {page_idx+1}에서 차단")
                break

            # 스냅샷 저장 (재파싱·검증용)
            (snap_dir / f"page_{page_idx+1:03d}.html").write_text(
                html, encoding="utf-8"
            )

            rows = parse_comments(html, salt)
            if not rows:
                logger.info("  단평 없음 → 종료")
                break

            for row in rows:
                if not in_date_range(row["date"], args.date_from,
                                     args.date_to):
                    continue
                row["book_id"] = book_id
                row["page"] = page_idx + 1
                row["crawl_timestamp"] = datetime.now(timezone.utc).isoformat()
                writer.writerow(row)
                collected += 1

            logger.info(f"  ✓ {len(rows)}건 파싱, 누적 {collected}건")
            f.flush()  # 차단 발생해도 데이터 손실 최소화

            # 다음 페이지 전 무작위 지연
            if page_idx < args.max_pages - 1:
                delay = random.uniform(args.delay_min, args.delay_max)
                logger.info(f"  ⏳ {delay:.1f}초 대기")
                time.sleep(delay)

    logger.info(f"=== 수집 종료 ===")
    logger.info(f"총 수집: {collected}건")
    logger.info(f"CSV: {csv_path}")
    logger.info(f"로그: {log_path}")
    logger.info(f"스냅샷: {snap_dir}")


if __name__ == "__main__":
    crawl(parse_args())
