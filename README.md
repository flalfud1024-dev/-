# 한강 『채식주의자』 독자 리뷰 크롤러

박사학위논문 데이터 수집 도구. **웹 GUI**로 누구나 사용 가능.

> **재현성 선언**: 본 저장소는 박사학위논문의 **재현성 증거물**입니다.
> 본문 부록에서 GitHub URL + commit hash로 인용됩니다.

---

## 🆕 PRD v1.0 도구: `scraper.py` (Windows 비프로그래머용)

PRD 기준으로 예스24 회원리뷰 + 한줄평을 한 번에 수집해 **Excel과 CSV로 동시
저장**하는 단일 스크립트입니다. 로그인·체크포인트·익명화 출력까지 포함합니다.

> 처음 사용하시면 아래 단계만 그대로 따라가세요. 명령은 모두 **복사 → 붙여넣기**
> 입니다.

### 1) 준비 (한 번만 하면 됩니다)

1. **Python 3.11 설치** — https://www.python.org/downloads/windows/
   설치 화면에서 **반드시 `Add python.exe to PATH` 체크**.
2. **크롬 브라우저 설치** — https://www.google.com/chrome/
3. **이 저장소 다운로드** — GitHub 페이지 초록색 `Code` → `Download ZIP` →
   압축 해제 (예: `C:\Users\YOUR\Documents\book-scraper`).
4. **명령 프롬프트(cmd)** 를 열고 한 줄씩 입력 (폴더 경로는 본인 것으로):
   ```cmd
   cd C:\Users\YOUR\Documents\book-scraper
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```
5. **환경 파일 만들기**
   ```cmd
   copy .env.example .env
   python -c "import secrets; print(secrets.token_hex(32))"
   ```
   - 마지막 명령이 출력한 긴 문자열을, 메모장으로 `.env`를 열어
     `ANONYMIZATION_SALT=` 뒤에 붙여넣고 저장.
   - 로그인 정보를 미리 넣어두려면 `YES24_ID`, `YES24_PW`도 채워둘 수 있습니다
     (비워두면 첫 실행 때 브라우저에서 직접 로그인하면 됩니다).

### 2) 첫 실행 — 시범 수집 (50페이지)

```cmd
venv\Scripts\activate
python scraper.py --id 108422348 --max-pages 50 --no-headless --login --anonymized
```

- 브라우저 창이 뜨고 예스24 로그인 페이지가 열립니다.
- 로그인을 완료한 뒤 **명령 창으로 돌아와 Enter** 를 누르면 수집이 시작됩니다.
- 이후부터는 쿠키가 `.auth/`에 저장돼 매번 로그인하지 않아도 됩니다.

### 3) 전체 리뷰 수집

```cmd
python scraper.py --id 108422348 --anonymized
```

- `--max-pages`를 빼면 끝까지 수집합니다.
- `--anonymized`는 닉네임을 뺀 **연구 공개용 별도 파일**을 함께 만듭니다.
- 중간에 끊겨도 같은 명령에 `--resume`만 추가하면 끊긴 지점부터 재개합니다.

### 4) 결과 파일 위치

```
output\
  9788936434595_채식주의자_20260511_1430.xlsx
  9788936434595_채식주의자_20260511_1430.csv             ← Excel에서 한글 안 깨짐
  9788936434595_채식주의자_20260511_1430_anonymized.xlsx ← 닉네임 제거본
  9788936434595_채식주의자_20260511_1430_anonymized.csv

logs\
  run_20260511_1430_108422348.log    ← 실행 기록

state\
  108422348_member.json              ← 체크포인트 (재시작용)
  108422348_oneliner.json
```

### 5) 다른 책 수집

```cmd
python scraper.py --url https://www.yes24.com/Product/Goods/XXXXXXXX --anonymized
```

### 자주 쓰는 옵션

| 옵션 | 설명 |
|------|------|
| `--id 108422348` | 예스24 상품 ID |
| `--url <URL>` | 상품 URL (둘 중 하나만) |
| `--types member,oneliner` | 종류 선택 (기본: 둘 다) |
| `--max-pages 50` | 종류별 최대 페이지 (0/생략 = 끝까지) |
| `--anonymized` | 닉네임 제거본 추가 생성 |
| `--no-headless` | 브라우저 창 보이기 (로그인·디버깅용) |
| `--login` | 강제로 로그인 절차 진행 |
| `--resume` | 체크포인트가 있으면 이어받기 |
| `--delay-min 1.0 --delay-max 3.0` | 요청 간 지연(초) |

### 문제가 생기면

- **`python is not recognized`** → Python 재설치, "Add to PATH" 체크.
- **로그인 자동 입력이 안 됨** → `--no-headless`로 창을 띄워 직접 로그인 후 Enter.
- **수집 0건** → `--no-headless`로 화면을 보며 어디서 멈추는지 확인.
  사이트 마크업이 바뀐 경우 `scraper.py` 상단 `SELECTORS` 영역만 수정.
- **중간 중단** → 같은 명령에 `--resume` 추가.

### 기존 GUI 도구와의 관계

기존 `app.py`(Streamlit GUI) 와 `crawler_yes24/crawl.py`는 그대로 두었습니다.
간단히 클릭으로 사용하려면 GUI를, PRD 사양대로 한 번에 정식 수집하려면
`scraper.py`를 쓰시면 됩니다.

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
