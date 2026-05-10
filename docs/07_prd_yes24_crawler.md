# PRD: Yes24 (한국) 독자 리뷰 수집 시스템

**문서 버전**: v1.0
**작성일**: 2026-05-10
**작성자**: 연구자 + AI 보조 (Claude, Anthropic 2025)
**대외자문**: 데이터사이언스 전공 ○○○ 선생님 (서울대학교)
**기반 자료**: `references/web_scraping_tutorial_summary.md` (Part 5)
**자매 PRD**: `docs/06_prd_douban_crawler.md`

> 본 PRD는 한·중 비교의 **한국 독자 기준선** 데이터를 수집한다. 豆瓣과 별개 시스템으로 운영되나, 다운스트림에서 동일 분석 파이프라인으로 통합된다.

---

## 1. 개요

### 1.1 시스템명
`vegetarian-yes24-crawler` — 한강 『채식주의자』 한국어 원본 도서의 Yes24 독자 리뷰·한줄평 자동 수집 시스템

### 1.2 한 문장 요약
> 박사학위논문의 **한국 독자 기준선**을 구축하기 위해, Yes24의 채식주의자 리뷰를 동적 페이지 렌더링을 통해 재현 가능하고 윤리적으로 수집하는 도구.

### 1.3 豆瓣 PRD와의 차이
| 항목 | 豆瓣 (06) | Yes24 (07, 본 문서) |
|------|----------|---------------------|
| 사이트 | 중국 도서 리뷰 플랫폼 | 한국 온라인 서점 |
| 페이지 유형 | 정적 (HTML 직송) | **동적 (JavaScript 렌더링)** |
| 기술 스택 | requests + BS4 | **Selenium + webdriver_manager** |
| 언어 | 중국어 (zh-CN) | **한국어 (ko-KR)** |
| 다운스트림 | jieba 형태소 분석 | **KoNLPy/Mecab 형태소 분석** |
| 감성사전 | DUTIR / BosonNLP | **KOSAC / KNU 한국어 감성사전** |
| 법적 영역 | 中 网络安全法 | **한국 저작권법, 정보통신망법** |

---

## 2. 배경 및 목적

### 2.1 연구 맥락 (한·중 비교 연구의 한국 baseline)
| 대상 | Yes24 상품 ID | 설명 |
|------|---------------|------|
| 한강, 『채식주의자』 (2007 창비 초판 또는 최신판) | `108422348` | 자료 §5에서 확인 |

> ⚠️ Yes24는 동일 도서의 여러 판본(초판/리커버/세트)이 별도 상품으로 등록되는 경향. 본 분석에 어느 판본을 포함할지 사전 결정 필요.

### 2.2 목적
- **G1**: 채식주의자 한국어 원본 리뷰 N ≥ 200건 + 한줄평 가능한 모든 건
- **G2**: 단일 명령으로 재현 가능한 수집
- **G3**: Yes24 이용약관 및 robots.txt 준수
- **G4**: 사용자 식별정보 익명화
- **G5**: 수집 시점·환경·로그 완전 기록

### 2.3 비목적
- 한강 다른 작품(소년이 온다, 작별하지 않는다 등) — 본 학위논문 범위 외
- 알라딘, 교보문고 등 타 한국 서점 — v2.0 이후 검토
- 책 외 정보(작가 인터뷰, 출판사 자료)

### 2.4 미결 사항
- **포함할 판본 수**: 단일 ID만? 모든 판본 통합?
- **노벨문학상(2024) 전후 분리 여부**: 수상 효과로 리뷰 양상이 급변. 코퍼스 분리 분석이 필요할 가능성.

---

## 3. 사용자 및 이해관계자

| 역할 | 책임 |
|------|------|
| 연구자(주사용자) | 수집 실행, 정제, 논문 작성 |
| 데이터사이언스 자문 | Selenium 트러블슈팅 자문 |
| 지도교수 | 윤리·방법론 승인 |
| Yes24 플랫폼 | 수집 대상 (ToS 준수) |
| 논문 심사위원회 | 재현성·윤리 검증 |

---

## 4. 범위

### 4.1 In-Scope
- ✅ 채식주의자 상품 페이지의 **회원 리뷰** 수집
- ✅ 채식주의자 상품 페이지의 **한줄평** 수집
- ✅ 메타데이터 (별점, 작성일, 유용/비유용 투표, 리뷰어 등급)
- ✅ 사용자 ID(또는 마스킹된 username) SHA-256 + salt 해싱
- ✅ 수집 로그 + 페이지 스냅샷 저장
- ✅ 중복 제거
- ✅ Resume 기능

### 4.2 Out-of-Scope
- ❌ 사용자 프로필 상세
- ❌ 댓글의 댓글
- ❌ 비공개·로그인 필요 영역 강제 접근
- ❌ Captcha 자동 우회

---

## 5. 기능 요구사항 (FR)

### FR-1: 설정 외부화
- Yes24 상품 ID 목록은 `config.yaml`에 정의
- 페이지 한도, 지연 범위, 노벨상 전후 기준일도 설정으로 관리

### FR-2: Selenium 드라이버 관리 (자료 패턴 채용)
```python
chrome_options = Options()
chrome_options.add_argument('--headless')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument('--disable-gpu')
chrome_options.add_argument('--window-size=1920,1080')
chrome_options.add_argument('--user-agent=Mozilla/5.0 ...')
```
- `webdriver_manager.chrome.ChromeDriverManager`로 드라이버 자동 설치
- 세션 종료 시 `driver.quit()` 의무화 (메모리 누수 방지)
- 명시적 대기(`WebDriverWait`)만 사용, `time.sleep`은 보조용

### FR-3: 리뷰 탭 진입
**URL**: `https://www.yes24.com/Product/Goods/{product_id}`

```python
review_tab = WebDriverWait(driver, 10).until(
    EC.element_to_be_clickable((By.CSS_SELECTOR, "a[href*='#review']"))
)
review_tab.click()
```

### FR-4: 페이지네이션
- Yes24 리뷰는 "더보기" 버튼 또는 페이지 번호 클릭으로 추가 로드
- 다음 페이지 버튼이 비활성화될 때까지 순회
- 페이지당 지연: `random.uniform(2, 5)` 초

### FR-5: 파싱 셀렉터 (자료 §5 + 검증 필요)
> ⚠️ 자료의 셀렉터는 검증되지 않음. 본 PRD M1 단계에서 실제 페이지 구조 확인 후 확정.

자료가 제시한 후보 셀렉터:
- `div.review_cont`
- `div.reviewInfoBot`
- `li.reviewInfoItem`

확정해야 할 필드:
| 필드 | 자료 상태 | M1에서 확정 |
|------|-----------|-------------|
| 리뷰 항목 | 후보 3종 | ✓ |
| 작성자 | 미정 | ✓ |
| 별점 | 미정 | ✓ |
| 본문 | 미정 | ✓ |
| 작성일 | 미정 | ✓ |
| 유용 투표 수 | 미정 | ✓ |
| 리뷰 유형 (리뷰/한줄평) | 미정 | ✓ |

### FR-6: 데이터 추출 항목
**필수**:
- `review_id` (Yes24 내부 ID 또는 페이지 내 순번)
- `source = 'yes24'`
- `product_id`
- `user_id_hash` (SHA-256 + salt)
- `rating` (1~10 또는 1~5; Yes24 정책 확인 필요)
- `text`
- `date` (ISO 8601)
- `helpful_votes`, `unhelpful_votes`
- `review_type` (review | one_line)
- `crawl_timestamp`
- `is_post_nobel` (2024-10-10 이후 작성 여부, **bool**)

**선택**:
- `reviewer_grade` (Yes24 등급)
- `book_edition` (판본 식별자)

### FR-7: 익명화
- 사용자 ID/username은 SHA-256 + 환경변수 `ANONYMIZATION_SALT`로 해싱
- 본문 내 개인정보 정규식 마스킹 (전화·이메일·주민번호 패턴)
- 익명화 키 `.env` 분리, `.gitignore` 등재

### FR-8: 중복 제거
- 1차: 동일 user_hash + 동일 작성일
- 2차: 텍스트 Levenshtein 유사도 ≤ 0.05

### FR-9: Resume
- 마지막 성공 페이지를 `state.json`에 저장
- 재실행 시 해당 페이지부터 재개
- 차단·드라이버 크래시 발생 시에도 데이터 손실 최소화

### FR-10: 로깅
- `logging` 모듈 사용
- 모든 페이지 진입·요소 탐색·클릭·실패 기록
- Selenium 예외(`TimeoutException`, `NoSuchElementException`) 별도 카운트

### FR-11: 출력 형식
- `data/raw/yes24_<product_id>_<YYYYMMDD>.csv` (UTF-8 BOM)
- `data/raw/_logs/yes24_<product_id>_<YYYYMMDD>.log`
- `data/raw/_snapshots/yes24/<product_id>/page_<N>.html`
- `data/raw/_state/yes24_<product_id>.json`

---

## 6. 비기능 요구사항 (NFR)

### NFR-1: 윤리 및 법적 적합성
- robots.txt 준수: `https://www.yes24.com/robots.txt` 확인 + 로그
- 요청 빈도: 페이지 로드 후 2~5초 지연, 분당 ≤ 20 페이지
- User-Agent: 정상 브라우저 식별자 단일 고정
- 인증 우회 금지
- **한국 정보통신망법 검토**: 자동화된 정보수집 도구 운용 관련
- IRB 검토: 학교 연구윤리심의 면제 여부 사전 확인

### NFR-2: 재현성
- 패키지 버전 고정 (Selenium, webdriver-manager, Chrome 버전 명시)
- 랜덤 시드 고정 (`RANDOM_SEED = 42`)
- 수집 시각 메타데이터 의무 기록
- 단일 명령 실행 (`python crawl.py --product <id>`)
- HTML 스냅샷 보존 → 사후 재파싱 가능

### NFR-3: 안정성
- Selenium 드라이버 크래시 시 재시작
- 부분 실패 시 데이터 즉시 flush
- 헤드리스 환경 메모리 모니터링

### NFR-4: 성능
- 200건 수집 시 약 60~90분 (Selenium은 정적보다 느림)
- 메모리 사용량 ≤ 2GB (Chrome 헤드리스 포함)

### NFR-5: 보안 및 프라이버시
- 익명화 salt 환경변수, 절대 커밋 금지
- 원본 user 식별자 디스크 저장 금지
- 출판 시 데이터셋 익명화 재검증

---

## 7. 데이터 스키마

```yaml
review:
  review_id:        string         # Yes24 ID 또는 순번
  source:           literal        # "yes24"
  product_id:       string         # 108422348 등
  user_id_hash:     string         # SHA-256(user_id + salt)
  rating:           int | null     # 1~10 (Yes24 표준)
  text:             string
  text_clean:       string         # 개인정보 마스킹 후
  date:             ISO 8601
  helpful_votes:    int
  unhelpful_votes:  int
  review_type:      enum           # review | one_line
  is_post_nobel:    bool           # 2024-10-10 이후
  reviewer_grade:   string | null  # Yes24 등급 (선택)
  book_edition:     string | null
  crawl_timestamp:  ISO 8601
  source_html_path: string
```

---

## 8. 기술 스택 (확정)

```
selenium==4.15.0
webdriver-manager==4.0.0
beautifulsoup4==4.12.0   # Selenium에서 가져온 page_source 파싱용
lxml==4.9.0
pyyaml==6.0.1
tenacity==8.2.0
python-Levenshtein
tqdm
python-dotenv
```

추가 환경 요구:
- Chrome 또는 Chromium 설치 필요
- (Linux/Colab) `--no-sandbox`, `--disable-dev-shm-usage` 옵션 필수

---

## 9. 디렉토리 구조 (豆瓣과 분리)

```
crawler_yes24/
├── README.md
├── config.yaml                 # 상품 ID 등
├── requirements.txt
├── .env.example
├── .gitignore
├── crawl.py                    # 진입점
├── modules/
│   ├── __init__.py
│   ├── driver_factory.py       # Chrome 드라이버 설정
│   ├── navigator.py            # 페이지 진입·탭 클릭·페이지네이션
│   ├── parser.py               # page_source → 리뷰 파싱
│   ├── anonymizer.py           # 공통 (豆瓣과 동일 모듈 재사용 권장)
│   ├── deduper.py              # 공통
│   ├── state.py                # resume
│   └── logger.py
├── tests/
│   ├── fixtures/
│   │   └── sample_yes24_review_page.html
│   └── test_parser.py
└── data/
    ├── raw/
    └── processed/
```

> ⚠️ `anonymizer.py`, `deduper.py`, `state.py`, `logger.py`는 豆瓣 시스템과 **동일 로직 공유**. 향후 `crawler_common/` 패키지로 분리 권장.

---

## 10. 마일스톤

| 단계 | 산출물 | 예상 기간 |
|------|--------|-----------|
| ✅ M0: PRD v1.0 확정 | 본 문서 | 완료 |
| M1: Yes24 페이지 구조 조사 | 셀렉터 확정 + 픽스처 HTML | 0.5주 |
| M2: 파서 단위테스트 | `parser.py` + 테스트 | 1주 |
| M3: Selenium PoC | 단일 페이지 진입·1페이지 수집 | 0.5주 |
| M4: 페이지네이션 + Resume | 200건 수집 | 1주 |
| M5: 본 수집 + 노벨상 분리 | `data/raw/yes24_*.csv` | 0.5주 |
| M6: 검증·부록화 | 부록 5에 통합 | 0.5주 |

---

## 11. 위험 및 완화

| 위험 | 영향 | 완화 |
|------|------|------|
| Yes24 페이지 구조 변경 | 파서 실패 | HTML 스냅샷 + M1에서 셀렉터 검증 |
| Selenium 탐지·차단 | 수집 중단 | 정상 헤더, 보수적 지연, 헤드리스 비활성화 옵션 |
| Chrome 버전 불일치 | 드라이버 오류 | webdriver-manager 자동 매칭 |
| Colab 메모리 한도 | OOM | 페이지별 driver 재생성 옵션 |
| 노벨상 효과로 리뷰 양상 급변 | 분석 혼란 | `is_post_nobel` 플래그로 사후 분리 분석 |
| 한국 ToS·정보통신망법 | 법적 리스크 | 학술 공정사용 검토 + IRB |

---

## 12. 수용 기준

- [ ] 채식주의자 N ≥ 200 리뷰 수집
- [ ] 데이터 스키마 필수 필드 결측률 ≤ 5%
- [ ] 익명화 검증: 원본 user 식별자 흔적 0건
- [ ] 동일 명령 재실행 시 동일 데이터셋 (timestamp 제외)
- [ ] parser 단위테스트 커버리지 ≥ 80%
- [ ] 수집 로그 전체 보존
- [ ] robots.txt 준수 로그 확인 가능
- [ ] HTML 스냅샷으로 사후 재파싱 가능
- [ ] 노벨상 전후 리뷰 분리 가능 (`is_post_nobel` 플래그)

---

## 13. 다운스트림 통합 설계

수집 후 한·중 비교 분석 파이프라인:

```
Yes24 (한국)              豆瓣 (중국)
   │                          │
   ▼                          ▼
KoNLPy/Mecab 형태소 분석    jieba 형태소 분석
   │                          │
   ▼                          ▼
KOSAC/KNU 감성사전          DUTIR/BosonNLP
   │                          │
   └──────────┬───────────────┘
              ▼
   언어중립 지표로 정규화
   (감성 극성, 강도, 토픽 분포)
              ▼
   한·중 비교 통계 검증
   (Mann-Whitney U, 효과크기)
```

**중요 주의사항**:
- 언어 간 직접 어휘 비교 불가 → **개념 수준의 비교 지표**로 변환 필요
- 감성사전이 다르면 점수 스케일이 다름 → 표준화(Z-score) 후 비교
- 토픽 모델링은 언어별 독립 실행 후 **토픽 의미를 연구자가 매핑**

→ 별도 문서 필요: `docs/08_cross_language_comparison_methodology.md` (예정)

---

## 14. 참고 문서
- `docs/06_prd_douban_crawler.md` — 자매 PRD
- `references/web_scraping_tutorial_summary.md` (Part 5) — 자문 자료
- `docs/01_research_design.md` — 연구 설계 (한·중 비교 추가 반영 필요)
- `docs/04_ai_disclosure.md` — AI 활용 공시

### 참고 문헌
- 백선(2025), 「문체 번역 가능성 연구: 『채식주의자』 한·중 독자 서평의 NLP 비교·분석」

---

## 변경 이력
- v1.0 (2026-05-10): 신규 작성. 豆瓣 PRD에서 Yes24 분리하여 별도 정의.
