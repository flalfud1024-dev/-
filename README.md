# 한강 『채식주의자』 독자 리뷰 크롤러

박사학위논문 데이터 수집 도구. **웹 GUI**로 누구나 사용 가능.

> **재현성 선언**: 본 저장소는 박사학위논문의 **재현성 증거물**입니다.
> 본문 부록에서 GitHub URL + commit hash로 인용됩니다.

---

## 🌟 빠른 시작 (3단계)

```bash
# 1. 설치
pip install -r requirements.txt

# 2. 환경변수 설정 (정식 분석용; 데모는 자동 생성됨)
cp .env.example .env
# .env에서 ANONYMIZATION_SALT 값을 채움
# 생성: python -c "import secrets; print(secrets.token_hex(32))"

# 3. 웹 GUI 실행
streamlit run app.py
```

→ 브라우저에 자동으로 `http://localhost:8501` 열림.

---

## 🖼️ GUI 사용 흐름

```
┌─────────────────────────────────────────────────────┐
│  📚 한강 『채식주의자』 독자 리뷰 크롤러                  │
├─────────────────────────────────────────────────────┤
│  [🇨🇳 더우반] [🇰🇷 Yes24] [❓ 도움말]                    │
│                                                     │
│  도서 선택  ◉ 후추통 2021  ○ 천일 2016  ○ 직접입력     │
│  도서 ID:   35534519                                │
│                                                     │
│  최대 페이지 [10▼]  정렬 [공감순▼]  상태 [읽음▼]        │
│  ☑ 날짜 필터    시작일 [    ]  종료일 [    ]           │
│                                                     │
│  [🚀 더우반 수집 시작]                                  │
│                                                     │
│  ▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░  페이지 5/10 수집 중…           │
│                                                     │
│  ✅ 수집 완료 — 100건                                  │
│  ┌───┬──────────┬───────┬────┬────┬──────────┐    │
│  │페이지│ 작성일   │작성자ID│별점│공감│  내용     │    │
│  ├───┼──────────┼───────┼────┼────┼──────────┤    │
│  │ 1 │2024-03-15│a1b2c3 │ 5  │156 │过于令人惊艳…│    │
│  │ 1 │2024-08-21│d4e5f6 │ 4  │ 89 │看得越多……   │    │
│  └───┴──────────┴───────┴────┴────┴──────────┘    │
│                                                     │
│  [📥 CSV 다운로드]                                     │
└─────────────────────────────────────────────────────┘
```

---

## 📋 두 가지 사용 방법

### 방법 1: 웹 GUI (권장 — 일반인 친화)

```bash
streamlit run app.py
```

- 링크 붙여넣기 → 조건 설정 → 클릭 → 표 확인 → 다운로드
- Python 코드 작성 불필요

### 방법 2: 명령줄 (CLI — 자동화·배치용)

```bash
python crawler_douban/crawl.py 35534519 --max-pages 20 --sort score
python crawler_yes24/crawl.py 108422348 --max-pages 20
```

---

## 🌐 외부 공개 옵션 (심사위원도 사용 가능)

본인 컴퓨터에서만 쓸 수도 있고, 공개 URL로 만들 수도 있습니다:

### A) 로컬 실행 (기본)
- `streamlit run app.py` → `localhost:8501`
- 본인만 접속 가능

### B) Streamlit Community Cloud (무료 공개)
1. https://share.streamlit.io 접속 (GitHub 로그인)
2. "New app" → 본 저장소 선택 → `app.py` 지정
3. 배포 후 공개 URL 획득 (예: `https://yourname-vegetarian.streamlit.app`)
4. ⚠️ Yes24(Selenium) 작동을 위해 `packages.txt`에 `chromium`, `chromium-driver` 추가 필요

### C) HuggingFace Spaces (대안)
- https://huggingface.co/spaces 에서 Streamlit 템플릿 선택
- 본 저장소 push

---

## 📂 폴더 구조

```
.
├── README.md                 # 본 문서
├── app.py                    # 🌟 Streamlit GUI 진입점
├── requirements.txt
├── .env.example
├── .gitignore
│
├── crawler_douban/
│   ├── crawl.py              # 더우반 크롤러 (CLI + 함수)
│   ├── config.yaml           # 정책 참조
│   └── README.md
│
├── crawler_yes24/
│   ├── crawl.py              # Yes24 크롤러 (Selenium)
│   └── README.md
│
├── code/                     # 텍스트마이닝 분석 (수집 후 단계)
├── docs/                     # 연구 설계·PRD·방법론
└── references/
```

---

## 🔬 바이브 코딩 + 박사논문 인용

본 저장소의 코드는 다음 협업으로 작성되었습니다:

```
Claude (AI)         데이터사이언스 자문            연구자
─────────           ──────────────────           ──────
바이브 코딩      →  코드·방법론 검토         →   최종 검증·심사 대응
```

### 논문 부록 5 인용 템플릿

```
[부록 5: 데이터 수집 도구]
저장소:    https://github.com/flalfud1024-dev/-
사용 도구: Streamlit GUI (app.py) — 본 저장소 루트
사용 커밋: <git rev-parse HEAD 결과를 여기에>
사용 예시:
  더우반: 도서 ID 35534519, max_pages=20, sort=score
  Yes24:  상품 ID 108422348, max_pages=20
환경:      Python 3.10.x, Chrome (Yes24용)
```

상세 공시 원칙: [`docs/04_ai_disclosure.md`](docs/04_ai_disclosure.md)

---

## ⚖️ 윤리·정책 요약

| 항목 | 정책 |
|------|------|
| 익명화 | 사용자명 SHA-256 + salt 해싱 |
| 요청 간격 | 페이지당 무작위 지연 |
| User-Agent | 정상 브라우저 단일 고정 (로테이션 미사용) |
| 403 대응 | 재시도 3회 후 즉시 중단, 그때까지 보존 |
| 스냅샷 | 원본 HTML 저장 (사후 검증) |
| 로그 | 모든 요청·응답 별도 파일 기록 |

---

## 🚧 진행 단계

```
✅ [현재] 웹크롤링 도구 (GUI + CLI)
⏳ [다음] 텍스트마이닝 분석 (사용자 요청 시)
```
