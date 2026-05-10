"""
🌟 한강 『채식주의자』 독자 리뷰 크롤러 — 웹 GUI

사용법:
  streamlit run app.py

기능:
  1. 더우반/Yes24 링크(또는 ID) 붙여넣기
  2. 페이지 수·정렬·날짜 등 조건 설정
  3. "수집 시작" 클릭
  4. 결과 표 즉시 확인
  5. CSV 다운로드 버튼
"""

import os
import secrets
from datetime import datetime
from io import StringIO

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from crawler_douban.crawl import (
    crawl_to_df as crawl_douban,
    extract_book_id,
    KNOWN_BOOKS,
)
from crawler_yes24.crawl import (
    crawl_to_df as crawl_yes24,
    extract_product_id,
    KNOWN_PRODUCTS,
)

# === 페이지 설정 ===
st.set_page_config(
    page_title="채식주의자 독자 리뷰 크롤러",
    page_icon="📚",
    layout="wide",
)

# === 환경변수 로드 + 자동 salt 생성 ===
load_dotenv()
if not os.environ.get("ANONYMIZATION_SALT") or \
   os.environ["ANONYMIZATION_SALT"].startswith("__REPLACE_ME__"):
    # 세션별로 자동 생성 (실험·데모용; 정식 분석에는 .env 고정값 사용 권장)
    if "auto_salt" not in st.session_state:
        st.session_state.auto_salt = secrets.token_hex(32)
    os.environ["ANONYMIZATION_SALT"] = st.session_state.auto_salt

# === 상단 ===
st.title("📚 한강 『채식주의자』 독자 리뷰 크롤러")
st.caption(
    "박사학위논문 데이터 수집용 · 바이브 코딩으로 작성 · "
    "[GitHub 저장소](https://github.com/flalfud1024-dev/-)"
)

# === 사이드바: 공통 설정 ===
with st.sidebar:
    st.header("⚙️ 공통 설정")

    salt_input = st.text_input(
        "익명화 Salt",
        value=os.environ.get("ANONYMIZATION_SALT", ""),
        type="password",
        help="사용자명 SHA-256 해싱에 사용. 같은 salt면 같은 사용자가 같은 해시 → "
             "동일 인물의 여러 리뷰 식별 가능. 분석 전 기간 동일 값 유지 권장.",
    )
    os.environ["ANONYMIZATION_SALT"] = salt_input

    save_files = st.checkbox(
        "📁 CSV·로그·HTML 스냅샷 파일 저장",
        value=True,
        help="끄면 메모리에서만 처리. 켜면 ./data/ 폴더에 저장 (논문 부록·재현성용).",
    )
    out_dir = st.text_input("저장 경로", value="data") if save_files else None

    st.divider()
    st.markdown("### 📌 박사논문 인용용")
    st.code(
        "저장소: https://github.com/flalfud1024-dev/-\n"
        "사용 커밋: <git rev-parse HEAD>\n"
        "도구: Streamlit GUI (app.py)",
        language=None,
    )

# === 탭 ===
tab_douban, tab_yes24, tab_help = st.tabs([
    "🇨🇳 더우반 (중국)",
    "🇰🇷 Yes24 (한국)",
    "❓ 도움말",
])


# ============================================================
# 더우반 탭
# ============================================================
with tab_douban:
    st.subheader("豆瓣 단평 수집")

    # 사전 등록 + 직접 입력
    options = ["📖 " + label for _, label in KNOWN_BOOKS.values()] + ["✏️ 직접 입력"]
    keys = list(KNOWN_BOOKS.keys()) + [None]
    sel_idx = st.radio(
        "도서 선택",
        range(len(options)),
        format_func=lambda i: options[i],
        horizontal=True,
        key="douban_select",
    )

    if keys[sel_idx] is not None:
        url_or_id = KNOWN_BOOKS[keys[sel_idx]][0]
        st.info(f"도서 ID: **{url_or_id}**")
    else:
        url_or_id = st.text_input(
            "豆瓣 URL 또는 도서 ID",
            placeholder="https://book.douban.com/subject/35534519/  또는  35534519",
        )

    st.markdown("##### 수집 조건")
    c1, c2, c3 = st.columns(3)
    max_pages = c1.number_input("최대 페이지 (×20건)", 1, 100, 10,
                                key="douban_pages")
    sort_label = c2.selectbox("정렬", ["공감순 (score)", "최신순 (new)"],
                              key="douban_sort")
    sort = "score" if "score" in sort_label else "new"
    status_label = c3.selectbox("상태", ["읽음 (P)", "읽는중 (F)", "읽고싶음 (W)"],
                                key="douban_status")
    status = status_label.split("(")[1][0]

    c4, c5 = st.columns(2)
    use_date = c4.checkbox("날짜 필터", key="douban_use_date")
    if use_date:
        col_a, col_b = st.columns(2)
        date_from = col_a.date_input("시작일", key="douban_dfrom")
        date_to = col_b.date_input("종료일", key="douban_dto")
        date_from_str = date_from.isoformat() if date_from else None
        date_to_str = date_to.isoformat() if date_to else None
    else:
        date_from_str = date_to_str = None

    if st.button("🚀 더우반 수집 시작", type="primary",
                 use_container_width=True, key="douban_run"):
        if not url_or_id:
            st.error("도서 URL 또는 ID를 입력해주세요.")
        elif not salt_input:
            st.error("사이드바에서 익명화 Salt를 설정해주세요.")
        else:
            try:
                book_id = extract_book_id(url_or_id)
            except ValueError as e:
                st.error(str(e))
                st.stop()

            # 진행률·로그 영역
            prog_bar = st.progress(0.0)
            status_text = st.empty()
            log_lines: list[str] = []
            log_box = st.expander("📜 실행 로그", expanded=False)
            log_placeholder = log_box.empty()

            def on_progress(cur, tot, msg):
                prog_bar.progress(min(cur / tot, 1.0))
                status_text.info(msg)

            def on_log(msg):
                log_lines.append(msg)
                log_placeholder.code("\n".join(log_lines[-30:]),
                                     language=None)

            with st.spinner("수집 중… 더우반은 페이지당 3~6초 지연 적용"):
                try:
                    df, meta = crawl_douban(
                        book_id,
                        max_pages=int(max_pages),
                        sort=sort,
                        status=status,
                        date_from=date_from_str,
                        date_to=date_to_str,
                        out_dir=out_dir if save_files else None,
                        progress_callback=on_progress,
                        log_callback=on_log,
                    )
                except Exception as e:
                    st.error(f"오류: {e}")
                    st.stop()

            # 결과
            if meta["aborted"]:
                st.warning(
                    f"⚠️ IP 차단으로 도중 중단 — 그때까지 수집한 "
                    f"**{meta['n_collected']}건** 보존됨"
                )
            else:
                st.success(f"✅ 수집 완료 — **{meta['n_collected']}건**")

            if len(df) > 0:
                # 표시용 컬럼 순서
                cols = ["page", "date", "user_id_hash", "rating",
                        "likes", "text"]
                cols = [c for c in cols if c in df.columns]
                st.dataframe(
                    df[cols],
                    use_container_width=True,
                    column_config={
                        "page":        st.column_config.NumberColumn("페이지", width="small"),
                        "date":        st.column_config.TextColumn("작성일", width="small"),
                        "user_id_hash": st.column_config.TextColumn("작성자ID(해시)", width="small"),
                        "rating":      st.column_config.NumberColumn("별점", width="small"),
                        "likes":       st.column_config.NumberColumn("공감", width="small"),
                        "text":        st.column_config.TextColumn("내용", width="large"),
                    },
                )

                # 다운로드 버튼
                csv_bytes = df.to_csv(index=False).encode("utf-8-sig")
                fname = f"douban_{book_id}_{datetime.now():%Y%m%d_%H%M%S}.csv"
                st.download_button(
                    "📥 CSV 다운로드",
                    csv_bytes,
                    file_name=fname,
                    mime="text/csv",
                    use_container_width=True,
                )

                if save_files:
                    st.caption(f"📁 파일도 저장됨: `{meta['csv_path']}`")


# ============================================================
# Yes24 탭
# ============================================================
with tab_yes24:
    st.subheader("Yes24 리뷰 수집 (Selenium)")
    st.warning(
        "⚠️ Chrome/Chromium 설치 필요. 첫 실행 시 ChromeDriver 자동 다운로드."
    )

    options_y = ["📖 " + label for _, label in KNOWN_PRODUCTS.values()] + ["✏️ 직접 입력"]
    keys_y = list(KNOWN_PRODUCTS.keys()) + [None]
    sel_idx_y = st.radio(
        "도서 선택",
        range(len(options_y)),
        format_func=lambda i: options_y[i],
        horizontal=True,
        key="yes24_select",
    )

    if keys_y[sel_idx_y] is not None:
        url_or_id_y = KNOWN_PRODUCTS[keys_y[sel_idx_y]][0]
        st.info(f"상품 ID: **{url_or_id_y}**")
    else:
        url_or_id_y = st.text_input(
            "Yes24 URL 또는 상품 ID",
            placeholder="https://www.yes24.com/Product/Goods/108422348  또는  108422348",
        )

    st.markdown("##### 수집 조건")
    c1y, c2y = st.columns(2)
    max_pages_y = c1y.number_input("최대 페이지", 1, 100, 10, key="yes24_pages")
    headless = c2y.checkbox("헤드리스 (브라우저 창 숨김)", value=True,
                            key="yes24_headless")

    use_date_y = st.checkbox("날짜 필터", key="yes24_use_date")
    if use_date_y:
        col_ay, col_by = st.columns(2)
        date_from_y = col_ay.date_input("시작일", key="yes24_dfrom")
        date_to_y = col_by.date_input("종료일", key="yes24_dto")
        date_from_str_y = date_from_y.isoformat() if date_from_y else None
        date_to_str_y = date_to_y.isoformat() if date_to_y else None
    else:
        date_from_str_y = date_to_str_y = None

    if st.button("🚀 Yes24 수집 시작", type="primary",
                 use_container_width=True, key="yes24_run"):
        if not url_or_id_y:
            st.error("상품 URL 또는 ID를 입력해주세요.")
        elif not salt_input:
            st.error("사이드바에서 익명화 Salt를 설정해주세요.")
        else:
            try:
                pid = extract_product_id(url_or_id_y)
            except ValueError as e:
                st.error(str(e))
                st.stop()

            prog_bar = st.progress(0.0)
            status_text = st.empty()
            log_lines: list[str] = []
            log_box = st.expander("📜 실행 로그", expanded=False)
            log_placeholder = log_box.empty()

            def on_progress(cur, tot, msg):
                prog_bar.progress(min(cur / tot, 1.0))
                status_text.info(msg)

            def on_log(msg):
                log_lines.append(msg)
                log_placeholder.code("\n".join(log_lines[-30:]),
                                     language=None)

            with st.spinner("수집 중… Selenium 브라우저 구동에 시간이 걸립니다"):
                try:
                    df_y, meta_y = crawl_yes24(
                        pid,
                        max_pages=int(max_pages_y),
                        date_from=date_from_str_y,
                        date_to=date_to_str_y,
                        headless=headless,
                        out_dir=out_dir if save_files else None,
                        progress_callback=on_progress,
                        log_callback=on_log,
                    )
                except Exception as e:
                    st.error(f"오류: {e}")
                    st.stop()

            if meta_y["aborted"]:
                st.warning(f"⚠️ 중단됨 — {meta_y['n_collected']}건 보존")
            else:
                st.success(f"✅ 수집 완료 — **{meta_y['n_collected']}건**")

            if len(df_y) > 0:
                cols_y = ["page", "date", "user_id_hash", "rating",
                          "helpful_votes", "is_post_nobel", "text"]
                cols_y = [c for c in cols_y if c in df_y.columns]
                st.dataframe(
                    df_y[cols_y],
                    use_container_width=True,
                    column_config={
                        "page":          st.column_config.NumberColumn("페이지", width="small"),
                        "date":          st.column_config.TextColumn("작성일", width="small"),
                        "user_id_hash":  st.column_config.TextColumn("작성자ID(해시)", width="small"),
                        "rating":        st.column_config.NumberColumn("별점", width="small"),
                        "helpful_votes": st.column_config.NumberColumn("공감", width="small"),
                        "is_post_nobel": st.column_config.CheckboxColumn("노벨상 이후"),
                        "text":          st.column_config.TextColumn("내용", width="large"),
                    },
                )

                csv_bytes_y = df_y.to_csv(index=False).encode("utf-8-sig")
                fname_y = f"yes24_{pid}_{datetime.now():%Y%m%d_%H%M%S}.csv"
                st.download_button(
                    "📥 CSV 다운로드",
                    csv_bytes_y,
                    file_name=fname_y,
                    mime="text/csv",
                    use_container_width=True,
                )

                if save_files:
                    st.caption(f"📁 파일도 저장됨: `{meta_y['csv_path']}`")


# ============================================================
# 도움말 탭
# ============================================================
with tab_help:
    st.markdown("""
### 🚀 처음 사용한다면

1. **사이드바에서 Salt 확인** (자동 생성됨, 정식 분석은 `.env`에 고정값 권장)
2. **탭 선택** — 더우반(중국) 또는 Yes24(한국)
3. **도서 선택** — 사전 등록된 3종 또는 직접 URL 입력
4. **조건 설정** — 페이지 수·정렬·날짜
5. **🚀 수집 시작** 클릭
6. 결과 표 확인 → **📥 CSV 다운로드**

---

### 📁 자동 생성되는 파일

`📁 파일 저장` 옵션이 켜진 경우 `./data/` 폴더에:

| 파일 | 내용 |
|------|------|
| `douban_<id>_<시각>.csv` | 수집 데이터 (분석에 사용) |
| `douban_<id>_<시각>.log` | 실행 로그 (재현성 증거) |
| `_snapshots/<id>/page_001.html` | 원본 HTML (사후 검증용) |

---

### ⚠️ 더우반 차단 안내

豆瓣은 자동화 탐지가 매우 강력합니다.
- 한 번에 너무 많은 페이지 수집하면 차단됩니다 (5~10페이지 한도 권장)
- 차단되면 **24시간 대기 후** 재시도
- 차단 발생 시점까지 수집된 데이터는 **CSV에 보존**됩니다

---

### 🔬 박사학위논문 인용

```
부록 5: 데이터 수집 도구
저장소:    https://github.com/flalfud1024-dev/-
사용 도구: Streamlit GUI (app.py)
사용 커밋: $(git rev-parse HEAD)
```

---

### 🔧 익명화 Salt 안내

- 사용자명 → SHA-256(사용자명 + salt) → 16자 해시
- 같은 salt로 처리하면 같은 사용자가 항상 같은 해시 → 분석 시 동일 인물 식별 가능
- 정식 분석에는 `.env`에 **고정값**을 두어야 일관성 유지

```bash
# salt 생성
python -c "import secrets; print(secrets.token_hex(32))"
```

생성된 값을 `.env` 파일에 `ANONYMIZATION_SALT=...`로 저장.
""")
