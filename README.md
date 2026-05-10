# 한강 『채식주의자』 중문 번역본 비교 연구

박사학위논문 데이터 수집·분석 코드 저장소.

> **재현성 선언**: 본 저장소는 박사학위논문의 **재현성 증거물**입니다.
> 본문 부록에서 GitHub 저장소 URL + commit hash로 인용됩니다.

---

## 본 저장소의 위치

```
[학위논문 본문]                    [본 저장소]
  └ 부록 5 데이터 수집      ──→     crawler_douban/  중국어 더우반 크롤러
  └ 부록 5 데이터 수집      ──→     crawler_yes24/   한국어 Yes24 크롤러
  └ 부록 2 분석 코드        ──→     code/            텍스트마이닝 코드
  └ 방법론 챕터 보조 자료    ──→     docs/            연구설계·PRD·방법론 노트
```

## 빠른 시작

```bash
# 1. 의존성 설치
pip install -r requirements.txt

# 2. 환경변수 설정 (익명화 salt + 연구자 이메일)
cp .env.example .env
# .env 편집

# 3. 더우반 수집 예시
python crawler_douban/crawl.py 35534519 --max-pages 20 --sort score

# 4. Yes24 수집 예시
python crawler_yes24/crawl.py 108422348 --max-pages 20
```

자세한 사용법은 각 폴더의 README 참조:
- [`crawler_douban/README.md`](crawler_douban/README.md)
- [`crawler_yes24/README.md`](crawler_yes24/README.md)

---

## 폴더 구조

```
.
├── README.md                    # 본 문서
├── requirements.txt             # Python 의존성
├── .env.example                 # 환경변수 템플릿 (salt, 이메일)
├── .gitignore
│
├── crawler_douban/              # 🇨🇳 중국어 더우반 크롤러
│   ├── crawl.py                 # 단일파일 실행 스크립트
│   ├── config.yaml              # 기본 정책 (참조용)
│   └── README.md
│
├── crawler_yes24/               # 🇰🇷 한국어 Yes24 크롤러
│   ├── crawl.py                 # Selenium 기반 단일파일 스크립트
│   ├── config.yaml
│   └── README.md
│
├── code/                        # 📊 텍스트마이닝 분석 코드 (별도 단계)
│   ├── 00_setup.py
│   ├── 01_preprocessing.py
│   ├── 02_tfidf.py
│   ├── 03_lda.py
│   ├── 04_sentiment.py          # 감성 극성+강도 3-layer
│   ├── 04b_sentiment_validation.py
│   ├── 04c_sentiment_stats.py
│   ├── 05_network.py
│   └── 06_statistics.py
│
├── docs/                        # 📝 연구 설계 + PRD + 방법론
│   ├── 01_research_design.md
│   ├── 02_thesis_outline.md
│   ├── 03_methodology_notes.md
│   ├── 04_ai_disclosure.md      # AI 활용 공시
│   ├── 05_sentiment_methodology.md
│   ├── 06_prd_douban_crawler.md
│   └── 07_prd_yes24_crawler.md
│
└── references/
    └── web_scraping_tutorial_summary.md  # 데이터사이언스 자문 자료
```

---

## 바이브 코딩(Vibe Coding) 공시

본 저장소의 코드는 다음 협업 구조로 작성되었습니다:

```
Claude (AI)         데이터사이언스 자문            연구자 (논문 책임자)
─────────           ──────────────────            ────────────────────
코드 초안 생성   →  방법론·코드 검토          →   최종 이해·수정·검증
바이브 코딩         (서울대학교 ○○○ 선생님)        심사 질문 대응
                                                  GitHub 공개로 재현성 보장
```

### 논문 본문 표기 (예시)

> 본 연구의 데이터 수집 코드는 AI 언어모델(Claude, Anthropic, 2025)을 활용한 바이브 코딩(vibe coding) 방식으로 작성되었으며, 데이터사이언스 전문가의 자문을 거쳐 연구자가 직접 검토·수정·검증하였다. 재현성을 보장하기 위해 코드 전문은 GitHub에 공개하였다 (저장소: {URL}, 사용 커밋: {commit hash}).

상세 공시 원칙은 [`docs/04_ai_disclosure.md`](docs/04_ai_disclosure.md) 참조.

---

## 재현성을 위한 인용 방법

수집·분석을 마친 후 논문 부록에서 다음 정보를 명시:

### 부록 5-1: 데이터 수집 (더우반)
```
저장소:     https://github.com/{USER}/{REPO}
사용 커밋:  {commit hash}
실행 일시:  YYYY-MM-DD HH:MM (KST)
실행 명령:  python crawler_douban/crawl.py 35534519 --max-pages 20 --sort score
수집 결과:  N건, data/douban_35534519_*.csv
환경:       Python 3.10.x, Linux/macOS
```

### 부록 5-2: 데이터 수집 (Yes24)
```
저장소:     (위와 동일)
사용 커밋:  {commit hash}
실행 명령:  python crawler_yes24/crawl.py 108422348 --max-pages 20
수집 결과:  N건, 노벨상 전후 분리 가능 (is_post_nobel 컬럼)
환경:       Python 3.10.x + Chrome
```

### 커밋 해시 얻는 법
```bash
git rev-parse HEAD          # 현재 커밋
git log --oneline -5         # 최근 5개
```

---

## 윤리·정책 요약

| 항목 | 정책 |
|------|------|
| 익명화 | 사용자명 SHA-256 + salt 해싱 (원본 식별자 저장 안 함) |
| 요청 간격 | 페이지당 무작위 지연 (3~6초 더우반, 2~5초 Yes24) |
| User-Agent | 정상 브라우저 단일 고정 (로테이션·우회 미사용) |
| 403 대응 | 재시도 3회 후 즉시 중단, 그때까지 수집분 보존 |
| 스냅샷 | 원본 HTML 전체 저장 (사후 재파싱·검증 가능) |
| 로그 | 모든 요청·응답 별도 파일 기록 |

---

## 진행 단계

```
✅ [현재 단계] 웹 크롤링 도구 완성
              ├ crawler_douban/crawl.py
              └ crawler_yes24/crawl.py
              
⏳ [다음 단계] 텍스트마이닝 분석 (사용자 요청 시 진행)
              ├ 전처리 (jieba / KoNLPy)
              ├ TF-IDF + LDA
              ├ 감성 분석 (3-layer)
              ├ 인물 네트워크
              └ 통계 검증
```

---

## 라이선스 / 데이터 사용

- 본 저장소의 **코드**는 학술 연구 목적으로 자유롭게 참조·재사용 가능합니다.
- **수집된 데이터**는 익명화 처리되어 있으나, 원 저작자(리뷰어)의 권리를 존중하여 본 학위논문 외 용도로 재배포하지 않습니다.
- 豆瓣 / Yes24 각 사이트의 이용약관을 준수합니다.
