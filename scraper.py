#!/usr/bin/env python3
"""
Yes24 도서 리뷰 크롤러 — PRD §9 메인 실행 스크립트

회원리뷰(긴 글) + 한줄평을 수집해 Excel/CSV로 저장한다.
체크포인트 저장/재시작, 로그인 세션 유지, 익명화 출력 옵션을 지원한다.

사용 예 (Windows CMD/PowerShell):
    python scraper.py --url https://www.yes24.com/Product/Goods/108422348
    python scraper.py --id 108422348 --max-pages 50 --anonymized
    python scraper.py --id 108422348 --types member          # 회원리뷰만
    python scraper.py --id 108422348 --types oneliner        # 한줄평만
    python scraper.py --id 108422348 --login --no-headless   # 첫 로그인

전체 옵션은: python scraper.py --help
"""
from __future__ import annotations

import argparse
import getpass
import hashlib
import json
import logging
import os
import random
import re
import sys
import time
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

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
from tenacity import retry, stop_after_attempt, wait_exponential
from webdriver_manager.chrome import ChromeDriverManager

# ============================================================
# 상수 / 설정
# ============================================================
DEFAULT_DELAY_MIN = 1.0
DEFAULT_DELAY_MAX = 3.0
RANDOM_SEED = 42
LOGIN_URL = "https://www.yes24.com/Templates/FTLogIn.aspx"
PRODUCT_URL_TMPL = "https://www.yes24.com/Product/Goods/{pid}"

# 사이트 구조 변경 시 이 한 곳만 수정한다.
SELECTORS = {
    # 책 메타
    "book_title": ["em.gd_name", "h2.gd_name", ".gd_name"],
    "book_author": ["span.gd_auth a", ".gd_auth"],
    "book_isbn": ["#infoset_specific td", ".tbl_info td"],

    # 회원리뷰 탭 트리거
    "tab_member": ["a#yesReviewTab", "a[href*='#review']", "a.reviewTab"],
    # 한줄평 탭 트리거
    "tab_oneliner": ["a#yesShortReview", "a[href*='#shortReview']",
                     "a.oneLineTab", "a[href*='#oneline']"],

    # 회원리뷰 리스트 컨테이너 → 각 아이템
    "member_items": ["div.reviewInfoGrp", "li.reviewInfoItem",
                     "li.reviewItem"],
    # 한줄평 리스트 컨테이너 → 각 아이템
    "oneliner_items": ["div.oneLineGrp", "li.oneLineItem",
                       "div.cmtInfoGrp"],

    # 공통 필드 (리뷰 한 건 내부)
    "author": [".info_writer", ".reviewWriter", "a.name", ".writer"],
    "rating": [".rating_grade em", ".cRating em", ".rating em"],
    "date":   [".info_date", ".reviewDate", ".date"],
    "text_member":   [".review_cont", ".reviewInfoBot", ".cont"],
    "text_oneliner": [".cmt_cont", ".oneLineCont", ".cont"],
    "like":   [".helpful_num", ".cntHelpful", ".like em"],
    "view":   [".info_view em", ".cntView", ".view em"],

    # 페이지네이션
    "next_page": ["a.bgYUI.next", "a.next", "a[onclick*='goPage']"],
}

FIELDNAMES = [
    "review_id", "book_title", "book_isbn", "review_type",
    "review_text", "rating", "like_count", "view_count",
    "author_nickname", "author_nickname_hash",
    "created_at", "collected_at", "source_url",
]
PUBLIC_FIELDNAMES = [c for c in FIELDNAMES if c != "author_nickname"]


# ============================================================
# 데이터 모델
# ============================================================
@dataclass
class Review:
    review_id: str
    book_title: str
    book_isbn: str
    review_type: str          # "회원리뷰" | "한줄평"
    review_text: str
    rating: str
    like_count: str
    view_count: str
    author_nickname: str
    author_nickname_hash: str
    created_at: str
    collected_at: str
    source_url: str


@dataclass
class RunConfig:
    product_id: str
    types: list[str]                          # ["member", "oneliner"]
    max_pages: int | None                     # None = 끝까지
    delay_min: float
    delay_max: float
    headless: bool
    login: bool
    anonymized: bool
    out_dir: Path
    state_dir: Path
    log_dir: Path
    auth_dir: Path
    salt: str
    resume: bool
    started_at: str = field(default_factory=lambda:
                            datetime.now().strftime("%Y%m%d_%H%M"))


# ============================================================
# 유틸
# ============================================================
def log() -> logging.Logger:
    return logging.getLogger("scraper")


def make_run_id(cfg: RunConfig) -> str:
    return f"{cfg.product_id}_{cfg.started_at}"


def hash_nick(nick: str, salt: str) -> str:
    if not nick:
        return ""
    return hashlib.sha256(f"{nick}{salt}".encode("utf-8")).hexdigest()[:16]


def extract_product_id(url_or_id: str) -> str:
    s = str(url_or_id).strip()
    if s.isdigit():
        return s
    m = re.search(r"/Goods/(\d+)", s)
    if not m:
        raise ValueError(f"URL 또는 상품ID 형식이 아닙니다: {url_or_id!r}")
    return m.group(1)


def first(soup_or_elem, selectors: Iterable[str]):
    for sel in selectors:
        found = soup_or_elem.select_one(sel)
        if found:
            return found
    return None


def first_text(soup_or_elem, selectors: Iterable[str], default: str = "") -> str:
    el = first(soup_or_elem, selectors)
    if not el:
        return default
    return re.sub(r"\s+", " ", el.get_text(strip=True))


def safe_int_text(text: str) -> str:
    m = re.search(r"\d[\d,]*", text or "")
    return m.group().replace(",", "") if m else ""


def normalize_date(text: str) -> str:
    m = re.search(r"(\d{4})[.\-/](\d{1,2})[.\-/](\d{1,2})", text or "")
    if not m:
        return ""
    y, mo, d = m.groups()
    return f"{y}-{int(mo):02d}-{int(d):02d}"


def random_delay(cfg: RunConfig) -> None:
    time.sleep(random.uniform(cfg.delay_min, cfg.delay_max))


# ============================================================
# 브라우저
# ============================================================
def make_driver(headless: bool, user_data_dir: Path) -> webdriver.Chrome:
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1366,900")
    opts.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
    user_data_dir.mkdir(parents=True, exist_ok=True)
    opts.add_argument(f"--user-data-dir={user_data_dir.resolve()}")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()),
                            options=opts)


def click_one_of(driver, selectors: list[str], timeout: float = 5.0) -> bool:
    wait = WebDriverWait(driver, timeout)
    for sel in selectors:
        try:
            el = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, sel)))
            driver.execute_script("arguments[0].click();", el)
            return True
        except (TimeoutException, NoSuchElementException):
            continue
    return False


# ============================================================
# 로그인
# ============================================================
def cookie_path(cfg: RunConfig) -> Path:
    return cfg.auth_dir / "yes24_cookies.json"


def save_cookies(driver, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(driver.get_cookies(), ensure_ascii=False,
                               indent=2), encoding="utf-8")
    log().info("쿠키 저장: %s", path)


def load_cookies(driver, path: Path) -> bool:
    if not path.exists():
        return False
    driver.get("https://www.yes24.com/")
    for c in json.loads(path.read_text(encoding="utf-8")):
        c.pop("sameSite", None)
        try:
            driver.add_cookie(c)
        except Exception:
            pass
    return True


def is_logged_in(driver) -> bool:
    """간단 휴리스틱: 상단 메뉴에 '로그아웃' 텍스트가 있으면 로그인 상태."""
    try:
        return "로그아웃" in driver.page_source or "logOut" in driver.page_source
    except Exception:
        return False


def do_login(driver, cfg: RunConfig) -> bool:
    """
    .env의 YES24_ID/YES24_PW가 있으면 자동 시도, 없으면 사용자 수동 로그인 대기.
    캡차/2FA가 뜨면 자동 입력은 실패하므로 항상 수동 폴백 가능하도록 한다.
    """
    user = os.environ.get("YES24_ID", "").strip()
    pw = os.environ.get("YES24_PW", "").strip()
    driver.get(LOGIN_URL)
    time.sleep(2)

    if user and pw and not cfg.headless:
        try:
            driver.find_element(By.ID, "SMemberID").send_keys(user)
            driver.find_element(By.ID, "SMemberPassword").send_keys(pw)
            driver.find_element(By.CSS_SELECTOR,
                                "button.btn_login, a#btnLogin").click()
            log().info("자동 로그인 시도 — 캡차/2FA 발생 시 창에서 수동 처리하세요.")
        except NoSuchElementException:
            log().warning("로그인 입력 필드를 찾지 못함 — 수동 로그인 대기")

    if cfg.headless:
        log().error("로그인은 헤드리스 모드에서 불가합니다. --no-headless로 실행하세요.")
        return False

    print("\n[로그인 안내]")
    print("브라우저 창에서 직접 로그인을 완료하세요.")
    print("로그인이 끝나면 이 터미널로 돌아와 Enter를 누르세요.")
    try:
        input(">>> 로그인 완료 후 Enter: ")
    except (EOFError, KeyboardInterrupt):
        return False

    if not is_logged_in(driver):
        log().warning("로그인 상태가 감지되지 않았지만 계속 진행합니다 "
                      "(사이트 마크업이 다를 수 있음).")
    save_cookies(driver, cookie_path(cfg))
    return True


# ============================================================
# 메타 + 파싱
# ============================================================
def fetch_book_meta(driver, pid: str) -> dict:
    driver.get(PRODUCT_URL_TMPL.format(pid=pid))
    time.sleep(2)
    soup = BeautifulSoup(driver.page_source, "lxml")
    title = first_text(soup, SELECTORS["book_title"], default="(제목 미상)")

    # ISBN: 상세 표 안에서 'ISBN'으로 시작하는 셀의 다음 셀
    isbn = ""
    for td in soup.select("th, td"):
        if td.get_text(strip=True).startswith("ISBN"):
            sib = td.find_next("td")
            if sib:
                isbn = re.sub(r"[^0-9Xx]", "", sib.get_text())
            break
    return {"title": title, "isbn": isbn}


def parse_member_items(html: str) -> list[BeautifulSoup]:
    soup = BeautifulSoup(html, "lxml")
    for sel in SELECTORS["member_items"]:
        items = soup.select(sel)
        if items:
            return items
    return []


def parse_oneliner_items(html: str) -> list[BeautifulSoup]:
    soup = BeautifulSoup(html, "lxml")
    for sel in SELECTORS["oneliner_items"]:
        items = soup.select(sel)
        if items:
            return items
    return []


def review_id_for(item: BeautifulSoup, fallback: str) -> str:
    for attr in ("data-review-no", "data-reviewno", "data-no", "id"):
        v = item.get(attr) if hasattr(item, "get") else None
        if v:
            return str(v)
    raw = (item.get_text(" ", strip=True) if item else fallback)[:200]
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def item_to_review(
    item: BeautifulSoup,
    *,
    review_type: str,
    book_title: str,
    book_isbn: str,
    source_url: str,
    salt: str,
) -> Review | None:
    text_sel = (SELECTORS["text_member"] if review_type == "회원리뷰"
                else SELECTORS["text_oneliner"])
    text = first_text(item, text_sel)
    if len(text) < 2:
        return None

    nick = first_text(item, SELECTORS["author"])
    rating_text = first_text(item, SELECTORS["rating"])
    like = safe_int_text(first_text(item, SELECTORS["like"]))
    view = safe_int_text(first_text(item, SELECTORS["view"]))
    date = normalize_date(first_text(item, SELECTORS["date"]))

    rid = review_id_for(item, fallback=f"{review_type}|{nick}|{date}|{text[:50]}")
    if not rid:
        return None
    rid = f"{review_type[:1]}-{rid}"

    return Review(
        review_id=rid,
        book_title=book_title,
        book_isbn=book_isbn,
        review_type=review_type,
        review_text=text,
        rating=safe_int_text(rating_text),
        like_count=like,
        view_count=view,
        author_nickname=nick,
        author_nickname_hash=hash_nick(nick, salt),
        created_at=date,
        collected_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        source_url=source_url,
    )


# ============================================================
# 페이지 순회
# ============================================================
@retry(stop=stop_after_attempt(3),
       wait=wait_exponential(multiplier=2, min=2, max=8),
       reraise=True)
def open_tab(driver, kind: str) -> None:
    key = "tab_member" if kind == "member" else "tab_oneliner"
    if not click_one_of(driver, SELECTORS[key], timeout=6):
        log().warning("%s 탭 트리거를 찾지 못함 — 현재 페이지에서 진행", kind)
    time.sleep(1.5)


def go_to_page(driver, page_num: int) -> bool:
    """Yes24 리뷰 페이지네이션은 일반적으로 goPage(n) JS 함수를 호출."""
    for fn in (f"goPage({page_num});",
               f"javascript:goPage({page_num});"):
        try:
            driver.execute_script(fn)
            time.sleep(1.5)
            return True
        except WebDriverException:
            continue
    return click_one_of(driver,
                        [f"a[onclick*='goPage({page_num})']",
                         f"a[onclick*='pageNum={page_num}']",
                         "a.bgYUI.next", "a.next"], timeout=4)


def collect_one_type(
    driver, cfg: RunConfig, kind: str, meta: dict,
    state: dict, jsonl_path: Path,
) -> int:
    """kind: 'member' | 'oneliner'. 한 종류 전체 수집."""
    label = "회원리뷰" if kind == "member" else "한줄평"
    product_url = PRODUCT_URL_TMPL.format(pid=cfg.product_id)

    if driver.current_url.split("#")[0] != product_url:
        driver.get(product_url)
        time.sleep(2)
    open_tab(driver, kind)

    seen_ids: set[str] = set(state.get("seen_ids", []))
    last_page = int(state.get("last_page", 0))
    page = last_page + 1
    if page > 1:
        log().info("[%s] 체크포인트 발견 — %d페이지부터 재개", label, page)
        go_to_page(driver, page)

    new_count = 0
    while True:
        if cfg.max_pages and (page - last_page) > cfg.max_pages:
            log().info("[%s] --max-pages 한도 도달 (%d페이지) — 종료",
                       label, cfg.max_pages)
            break

        html = driver.page_source
        items = (parse_member_items(html) if kind == "member"
                 else parse_oneliner_items(html))
        if not items:
            log().info("[%s] 페이지 %d: 항목 0건 → 종료", label, page)
            break

        page_new = 0
        with jsonl_path.open("a", encoding="utf-8") as f:
            for it in items:
                rev = item_to_review(
                    it, review_type=label,
                    book_title=meta["title"], book_isbn=meta["isbn"],
                    source_url=product_url, salt=cfg.salt,
                )
                if not rev or rev.review_id in seen_ids:
                    continue
                seen_ids.add(rev.review_id)
                f.write(json.dumps(asdict(rev), ensure_ascii=False) + "\n")
                page_new += 1

        new_count += page_new
        log().info("[%s] 페이지 %d → 신규 %d건 (누적 %d)",
                   label, page, page_new, new_count)

        # 체크포인트 갱신
        state["last_page"] = page
        state["seen_ids"] = list(seen_ids)
        (cfg.state_dir / f"{cfg.product_id}_{kind}.json").write_text(
            json.dumps(state, ensure_ascii=False), encoding="utf-8")

        # 다음 페이지로
        next_page = page + 1
        if not go_to_page(driver, next_page):
            log().info("[%s] 다음 페이지 이동 실패 → 종료", label)
            break
        # 페이지 변경 감지 (HTML이 그대로면 마지막 페이지로 간주)
        time.sleep(0.5)
        if driver.page_source == html:
            log().info("[%s] 페이지 변동 없음 → 마지막 페이지로 판단", label)
            break

        page = next_page
        random_delay(cfg)

    return new_count


# ============================================================
# 출력
# ============================================================
def write_outputs(cfg: RunConfig, jsonl_paths: list[Path], meta: dict) -> dict:
    rows: list[dict] = []
    for p in jsonl_paths:
        if not p.exists():
            continue
        with p.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
    df = pd.DataFrame(rows, columns=FIELDNAMES)
    # 같은 review_id가 다른 페이지에서 중복 수집되는 경우 1회만 유지
    df = df.drop_duplicates(subset=["review_id"]).reset_index(drop=True)

    safe_title = re.sub(r"[\\/:*?\"<>|]", "_", meta["title"])[:40] or "book"
    stem = f"{meta['isbn'] or cfg.product_id}_{safe_title}_{cfg.started_at}"
    xlsx = cfg.out_dir / f"{stem}.xlsx"
    csv = cfg.out_dir / f"{stem}.csv"
    df.to_excel(xlsx, index=False)
    df.to_csv(csv, index=False, encoding="utf-8-sig")

    paths = {"xlsx": str(xlsx), "csv": str(csv), "n": len(df)}

    if cfg.anonymized:
        df_anon = df.drop(columns=["author_nickname"])
        xlsx_a = cfg.out_dir / f"{stem}_anonymized.xlsx"
        csv_a = cfg.out_dir / f"{stem}_anonymized.csv"
        df_anon.to_excel(xlsx_a, index=False)
        df_anon.to_csv(csv_a, index=False, encoding="utf-8-sig")
        paths.update({"xlsx_anonymized": str(xlsx_a),
                      "csv_anonymized": str(csv_a)})
    return paths


# ============================================================
# 메인
# ============================================================
def setup_logging(cfg: RunConfig) -> None:
    cfg.log_dir.mkdir(parents=True, exist_ok=True)
    logfile = cfg.log_dir / f"run_{cfg.started_at}_{cfg.product_id}.log"
    fmt = "%(asctime)s %(levelname)s %(message)s"
    logging.basicConfig(
        level=logging.INFO,
        format=fmt,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(logfile, encoding="utf-8"),
        ],
    )
    log().info("로그 파일: %s", logfile)


def build_config(args: argparse.Namespace) -> RunConfig:
    load_dotenv()
    salt = os.environ.get("ANONYMIZATION_SALT", "").strip()
    if not salt or salt.startswith("__REPLACE_ME__"):
        raise SystemExit(
            "❌ ANONYMIZATION_SALT가 설정되지 않았습니다.\n"
            "   .env.example을 .env로 복사한 뒤 ANONYMIZATION_SALT를 채워주세요.\n"
            "   값 생성: python -c \"import secrets; print(secrets.token_hex(32))\""
        )
    pid = extract_product_id(args.url or args.id)
    out_dir = Path(args.out_dir)
    base = Path(".")
    return RunConfig(
        product_id=pid,
        types=[t.strip() for t in args.types.split(",") if t.strip()],
        max_pages=args.max_pages or None,
        delay_min=args.delay_min,
        delay_max=args.delay_max,
        headless=not args.no_headless,
        login=args.login,
        anonymized=args.anonymized,
        out_dir=out_dir,
        state_dir=base / "state",
        log_dir=base / "logs",
        auth_dir=base / ".auth",
        salt=salt,
        resume=args.resume,
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Yes24 도서 리뷰 크롤러 (회원리뷰 + 한줄평)",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    tg = p.add_mutually_exclusive_group(required=True)
    tg.add_argument("--url", help="예스24 상품 URL")
    tg.add_argument("--id", help="예스24 상품 ID (숫자)")

    p.add_argument("--types", default="member,oneliner",
                   help="수집할 종류: member,oneliner (기본: 둘 다)")
    p.add_argument("--max-pages", type=int, default=0,
                   help="종류별 최대 페이지 (0=끝까지, 기본 0)")
    p.add_argument("--out-dir", default="output", help="결과 저장 폴더")
    p.add_argument("--delay-min", type=float, default=DEFAULT_DELAY_MIN)
    p.add_argument("--delay-max", type=float, default=DEFAULT_DELAY_MAX)
    p.add_argument("--no-headless", action="store_true",
                   help="브라우저 창을 보이게 (로그인·디버깅 시 권장)")
    p.add_argument("--login", action="store_true",
                   help="실행 전 로그인 (저장된 쿠키 무시)")
    p.add_argument("--anonymized", action="store_true",
                   help="닉네임 원본을 뺀 익명화 파일을 함께 생성")
    p.add_argument("--resume", action="store_true",
                   help="state/ 의 체크포인트가 있으면 이어받기")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    cfg = build_config(args)
    cfg.out_dir.mkdir(parents=True, exist_ok=True)
    cfg.state_dir.mkdir(parents=True, exist_ok=True)
    cfg.auth_dir.mkdir(parents=True, exist_ok=True)
    setup_logging(cfg)
    random.seed(RANDOM_SEED)

    log().info("=== Yes24 수집 시작 — 상품 %s ===", cfg.product_id)
    log().info("종류=%s 최대페이지=%s 익명화출력=%s 헤드리스=%s",
               cfg.types, cfg.max_pages or "∞", cfg.anonymized, cfg.headless)

    driver = make_driver(cfg.headless, user_data_dir=cfg.auth_dir / "profile")
    jsonl_paths: list[Path] = []
    try:
        # 쿠키 로드 시도
        if not cfg.login and load_cookies(driver, cookie_path(cfg)):
            driver.get(PRODUCT_URL_TMPL.format(pid=cfg.product_id))
            time.sleep(2)
            if is_logged_in(driver):
                log().info("저장된 쿠키로 로그인 상태 유지")
            else:
                log().info("저장된 쿠키가 만료된 듯 — 비로그인 상태로 진행")

        if cfg.login:
            if not do_login(driver, cfg):
                log().error("로그인 실패")
                return 2

        meta = fetch_book_meta(driver, cfg.product_id)
        log().info("도서: %s / ISBN=%s", meta["title"], meta["isbn"] or "?")

        type_map = {"member": "회원리뷰", "oneliner": "한줄평"}
        for kind in cfg.types:
            if kind not in type_map:
                log().warning("알 수 없는 종류 무시: %s", kind)
                continue
            jsonl = cfg.state_dir / f"{cfg.product_id}_{kind}.jsonl"
            jsonl_paths.append(jsonl)
            if not cfg.resume and jsonl.exists():
                jsonl.unlink()
            state_path = cfg.state_dir / f"{cfg.product_id}_{kind}.json"
            state = (json.loads(state_path.read_text(encoding="utf-8"))
                     if (cfg.resume and state_path.exists()) else {})
            collect_one_type(driver, cfg, kind, meta, state, jsonl)

        paths = write_outputs(cfg, jsonl_paths, meta)
        log().info("=== 수집 완료 — 총 %d건 ===", paths["n"])
        log().info("Excel: %s", paths["xlsx"])
        log().info("CSV  : %s", paths["csv"])
        if cfg.anonymized:
            log().info("익명화 Excel: %s", paths["xlsx_anonymized"])
            log().info("익명화 CSV  : %s", paths["csv_anonymized"])
        return 0

    except KeyboardInterrupt:
        log().warning("사용자 중단 — 체크포인트는 저장된 상태로 유지됨")
        return 130
    except WebDriverException as e:
        log().error("브라우저 오류: %s", e)
        return 3
    finally:
        try:
            driver.quit()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
