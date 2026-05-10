# PRD: 豆瓣 (중국) 독자 리뷰 수집 시스템

**문서 버전**: v1.1 (Yes24 분리 결정 반영)
**작성일**: 2026-05-10
**작성자**: 연구자 + AI 보조 (Claude, Anthropic 2025)
**대외자문**: 데이터사이언스 전공 ○○○ 선생님 (서울대학교)
**기반 자료**: `references/web_scraping_tutorial_summary.md`

> 본 문서는 박사학위논문 데이터 수집의 **재현성·연구윤리·법적 적합성**을 동시에 충족하기 위한 시스템 요구사항을 정의한다. 자문 자료(`web_scraping_tutorial.ipynb`)의 검증된 패턴을 차용하되, 재현성·익명화·테스트 가능성을 강화한다.

---

## 0. v0.1 → v1.0 변경 요약

| 항목 | v0.1 | v1.0 |
|------|------|------|
| 도서 ID | 미정 | `35534519` / `26735623` / `24847418` 확정 |
| 기술 스택 | 후보 비교 | requests+BS4 (豆瓣) 확정 |
| 페이지네이션 | 일반론 | URL 패턴 확정 |
| 파싱 셀렉터 | 미정 | 7개 필드 셀렉터 확정 |
| IP 차단 위험 | 일반 위험 | **자료에서 5페이지 후 차단 관측됨** — 대응 전략 강화 |
| Yes24 한국 리뷰 | 미언급 | **스코프 결정 미결** (§2.4) |

---

## 1. 개요

### 1.1 시스템명
`vegetarian-douban-crawler` — 한강 『채식주의자』 중문 번역본 3종의 豆瓣 독자 리뷰 자동 수집 시스템

### 1.2 한 문장 요약
> 박사학위논문 텍스트마이닝 분석을 위해, 3개 번역본의 豆瓣 독자 리뷰(단평·서평)를 **재현 가능하고 윤리적으로** 수집하는 도구.

---

## 2. 배경 및 목적

### 2.1 연구 맥락 (확정)
| 번역본 | 豆瓣 도서 ID | 출판사 |
|--------|--------------|--------|
| 후추통 2021 (간체) | `35534519` | 四川文艺出版社 |
| 천일 2016 (번체, 타이완) | `26735623` | 漫遊者文化 |
| 천일 2013 (간체, 본토) | `24847418` | 重庆出版社 |

### 2.2 목적
- **G1**: 3개 번역본 각각 최소 200건 이상의 유효 단평 + 가능한 모든 장평 확보
- **G2**: 모든 수집 작업이 단일 명령으로 재실행 가능
- **G3**: 豆瓣 이용약관 및 robots.txt 준수
- **G4**: 사용자 식별정보 익명화 처리 (IRB 윤리)
- **G5**: 수집 시점·환경·로그 완전 기록

### 2.3 비목적
- 微博, 小红书 등 타 플랫폼 — v2.0 이후 검토
- 사용자 프로필·팔로워 정보
- 비공개 콘텐츠 강제 접근

### 2.4 한국 독자 서평(Yes24)과의 관계 — **별도 PRD로 분리 (해소)**
본 학위논문은 **한국 독자(Yes24)를 기준으로 중국 독자(豆瓣)와 비교**하는 한·중 양국 비교 연구이며, 추가로 중국 독자 내부에서 번역본별(2013 vs 2021) 차이를 분석한다.

사이트·기술스택·언어·법적 영역이 상이하므로 본 PRD는 **豆瓣 수집만 정의**하며, Yes24 수집은 `docs/07_prd_yes24_crawler.md`에서 별도로 정의한다.

두 시스템의 출력은 다운스트림에서 통합되어 한·중 비교 분석에 사용된다.

---

## 3. 사용자 및 이해관계자

| 역할 | 책임 |
|------|------|
| 연구자(주사용자) | 수집 실행, 데이터 정제, 논문 작성 |
| 데이터사이언스 자문 | 코드 검토, 셀렉터·차단 대응 자문 |
| 지도교수 | 윤리·방법론 승인 |
| 豆瓣 플랫폼 | 수집 대상 (ToS 준수) |
| 논문 심사위원회 | 재현성·윤리 검증 |

---

## 4. 범위

### 4.1 In-Scope
- ✅ 3개 도서의 短评(short comment) 수집 — 목표 페이지 ≥ 10
- ✅ 3개 도서의 影评(long review) 수집 — 가능한 모든 페이지
- ✅ 메타데이터 (별점, 작성일, 좋아요 수, 본문)
- ✅ 사용자 ID SHA-256 + salt 해싱
- ✅ 수집 로그 + 원본 HTML 스냅샷 저장
- ✅ 중복 제거 (review_id 기반 + 텍스트 fuzzy)
- ✅ 차단 발생 후 resume 기능

### 4.2 Out-of-Scope
- ❌ 사용자 프로필·팔로워 정보
- ❌ 댓글의 댓글
- ❌ 비공개·로그인 필요 콘텐츠
- ❌ Captcha 자동 우회
- ❌ IP 우회·VPN

---

## 5. 기능 요구사항 (FR)

### FR-1: 설정 외부화
- 도서 ID, 페이지 한도, 지연 범위는 `config.yaml`에 정의
- ID 변경 시 코드 수정 없이 설정만으로 대응

### FR-2: 短评 수집 (자료 패턴 채용 + 강화)
**URL**: `https://book.douban.com/subject/{book_id}/comments/?start={N}&limit=20&status=P&sort=score`

**파싱 셀렉터** (자료에서 확정):
| 필드 | 셀렉터 |
|------|--------|
| 항목 | `li.comment-item` |
| 사용자명 | `span.comment-info a` |
| 평점 | `span.comment-info span[class*="rating"]` (`allstar{N}0` → N) |
| 날짜 | `span.comment-info span.comment-time` |
| 본문 | `span.short` |
| 좋아요 | `span.vote-count` |

**지연**: `random.uniform(3, 6)` 초 (자료 2~4초보다 강화)

### FR-3: 影评 수집
**URL**: `https://book.douban.com/subject/{book_id}/reviews?start={N}`

**파싱 셀렉터**:
| 필드 | 셀렉터 |
|------|--------|
| 항목 | `div.review-item` |
| 제목 | `h2 a` |
| 작성자 | `header.main-hd a.name` |
| 평점 | `span[class*="rating"]` |
| 본문(요약) | `div.short-content` |

### FR-4: HTTP 요청 (자료 헤더 채용)
```python
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,ko;q=0.7',
    'Referer': 'https://book.douban.com/',
}
```

**연락처 헤더 추가** (학술 연구 명시):
```python
headers['From'] = '연구자_이메일@hufs.ac.kr'
```

### FR-5: 데이터 추출 항목
**필수**:
- `review_id`, `version`, `user_id_hash` (SHA-256+salt)
- `rating` (1~5 또는 None)
- `text`, `date`, `likes`
- `crawl_timestamp`, `is_long_review`

**선택**: `reply_count`, `review_url`

### FR-6: 익명화 처리 (자료에 없음 — 신규)
- 사용자 ID는 SHA-256 + 환경변수 `ANONYMIZATION_SALT`로 해싱
- 본문 내 명시적 개인정보(전화번호·이메일) 정규식 마스킹
- 익명화 키는 `.env`로 관리, `.gitignore` 등재

### FR-7: 중복 제거 (자료에 없음 — 신규)
- 1차: `review_id` 기준
- 2차: 텍스트 Levenshtein 유사도 ≤ 0.05 (재게시·표절 제거)

### FR-8: 차단 대응 + Resume (자료의 실패 보강)
- 자료에서 5페이지 후 IP 차단 관측 → 다음 정책 적용:
  1. **403 발생 시 즉시 중단** (재시도 ≤ 3회만)
  2. **마지막 성공 페이지를 `state.json`에 저장**
  3. **다음 실행 시 해당 페이지부터 재개**
  4. 차단 누적 시 24시간 휴지 후 재시도 권고
- ❌ User-Agent 로테이션·프록시는 윤리 검토 후 결정 (현재 보류)

### FR-9: 로깅 (자료의 print 보강)
- `logging` 모듈 사용
- 모든 HTTP 요청·응답 코드·재시도 기록
- 세션별 요약 통계 (요청 수, 성공/실패, 소요 시간)
- 원본 HTML 스냅샷 저장

### FR-10: 출력 형식
- `data/raw/<version>_<YYYYMMDD>.csv` (UTF-8 BOM)
- `data/raw/_logs/<version>_<YYYYMMDD>.log`
- `data/raw/_snapshots/<version>/comments_<page>.html`
- `data/raw/_state/<version>.json` (resume용)

---

## 6. 비기능 요구사항 (NFR)

### NFR-1: 윤리 및 법적 적합성 (최우선)
- robots.txt 준수: 수집 전 확인 + 로그
- 요청 빈도: 페이지당 3~6초, 분당 ≤ 15 요청 (자료보다 보수적)
- User-Agent: 정상 브라우저 식별자 **단일 고정** (로테이션 보류)
- 인증 우회 금지
- 학술 목적 명시 (From 헤더 또는 contact)
- IRB 검토: 학교 연구윤리심의 면제 사전 확인

### NFR-2: 재현성
- 패키지 버전 고정 (`requirements.txt`)
- 랜덤 시드 고정 (`RANDOM_SEED = 42`) — 지연 무작위성도 시드 기반
- 수집 시각 메타데이터 의무 기록
- 단일 명령 실행 (`python crawl.py --version all`)
- HTML 스냅샷 보존 → 사후 재파싱 가능

### NFR-3: 안정성
- 차단·네트워크 단절 시 resume 기능
- 부분 실패 시에도 수집 데이터 즉시 디스크 flush

### NFR-4: 성능
- 번역본 1개당 200건 수집 시 약 30~60분 (지연 포함)
- 메모리 사용량 ≤ 1GB

### NFR-5: 보안 및 프라이버시
- 익명화 salt는 환경변수, **절대 커밋 금지** (`.gitignore` 등재)
- 원본 user_id 디스크 저장 금지
- 출판 시 데이터셋 공개 전 익명화 재검증

---

## 7. 데이터 스키마

```yaml
review:
  review_id:        string         # 豆瓣 고유 ID
  version:          enum           # tianyi_2013 | taiwan_2016 | huchutong_2021
  user_id_hash:     string         # SHA-256(user_id + salt)
  rating:           int | null     # 1~5
  text:             string         # 본문 (정제 전)
  text_clean:       string         # 정제 후 (개인정보 마스킹)
  date:             ISO 8601
  likes:            int
  reply_count:      int
  is_long_review:   bool
  review_url:       string
  crawl_timestamp:  ISO 8601
  source_html_path: string
```

---

## 8. 기술 스택 (확정)

```
requests==2.31.0
beautifulsoup4==4.12.0
lxml==4.9.0
pyyaml==6.0.1
tenacity==8.2.0       # 재시도 로직
python-Levenshtein    # 중복 제거
tqdm                  # 진행률
python-dotenv         # 환경변수
```

> Selenium은 **Yes24 스코프 결정 후** 추가.

---

## 9. 디렉토리 구조

```
crawler/
├── README.md
├── config.yaml
├── requirements.txt
├── .env.example                # ANONYMIZATION_SALT, RESEARCHER_EMAIL
├── .gitignore                  # .env, data/raw/, snapshots/
├── crawl.py                    # 진입점
├── modules/
│   ├── __init__.py
│   ├── fetcher.py              # HTTP 요청 + 재시도
│   ├── parser_comments.py      # 단평 파싱
│   ├── parser_reviews.py       # 장평 파싱
│   ├── anonymizer.py           # SHA-256 해싱
│   ├── deduper.py              # 중복 제거
│   ├── state.py                # resume용 상태 관리
│   └── logger.py
├── tests/
│   ├── fixtures/
│   │   ├── sample_comment_page.html
│   │   └── sample_review_page.html
│   ├── test_parser_comments.py
│   ├── test_parser_reviews.py
│   └── test_anonymizer.py
└── data/
    ├── raw/
    │   ├── _logs/
    │   ├── _snapshots/
    │   └── _state/
    └── processed/
```

---

## 10. 마일스톤

| 단계 | 산출물 | 예상 기간 |
|------|--------|-----------|
| ✅ M0: PRD v1.0 확정 | 본 문서 | 완료 |
| M1: 파서 단위테스트 | `parser_*.py` + HTML 픽스처 | 1주 |
| M2: 단일 페이지 PoC | 단평 1페이지 수집 + 익명화 | 0.5주 |
| M3: 페이지네이션 + Resume | 번역본 1개 200건 수집 | 1주 |
| M4: 3개 번역본 본 수집 | `data/raw/*.csv` 완성 | 1~2주 (차단 대응 포함) |
| M5: 장평 수집 | `*_reviews.csv` 추가 | 0.5주 |
| M6: 검증·부록화 | 부록 5 문서, 코드 정리 | 0.5주 |

---

## 11. 위험 및 완화

| 위험 | 영향 | 완화 |
|------|------|------|
| **豆瓣 IP 차단 (관측됨)** | 수집 중단 | 지연 강화(3~6s) + Resume + 24h 휴지 |
| 페이지 구조 변경 | 파서 실패 | HTML 스냅샷 저장 → 사후 재파싱 |
| 로그인 페이지 등장 | 일부 데이터 손실 | 공개 영역만 수집, 한계로 명시 |
| 중복·스팸 | 노이즈 | FR-7 이중 중복 제거 |
| ToS 위반 우려 | 윤리·법적 | 자문 + IRB + 공정사용 검토 |
| 표본 부족 (200 미달) | 통계 검증 약화 | 분석 범위 조정, 한계로 명시 |
| User-Agent 로테이션 유혹 | 윤리 위반 | 보류 — 지도교수 협의 전 사용 금지 |

---

## 12. 수용 기준

본 PRD가 충족되었다고 판단하는 기준:

- [ ] 3개 번역본 각각 N ≥ 200 단평 수집 (또는 사이트 한도 내 최대)
- [ ] 데이터 스키마 필수 필드 결측률 ≤ 5%
- [ ] 익명화 검증: 원본 user_id 흔적 0건
- [ ] 동일 명령 재실행 시 동일 데이터셋 (timestamp 제외)
- [ ] 단위테스트 커버리지 ≥ 80% (parser·anonymizer)
- [ ] 수집 로그 전체 보존 (오류·재시도 포함)
- [ ] robots.txt 준수 로그 확인 가능
- [ ] HTML 스냅샷으로 사후 재파싱 가능

---

## 13. 자문 자료에서 학습한 핵심 결정사항

| 결정 | 자료 근거 |
|------|-----------|
| 도서 ID 3종 확정 | 자료 §4 코드 셀 |
| URL 패턴 (`?start=N&limit=20&status=P&sort=score`) | 자료 §4 코드 |
| 파싱 셀렉터 7종 | 자료 `parse_comments()` |
| 평점 변환식 (`allstar{N}0` // 10) | 자료 코드 |
| **지연 시간 강화 (2~4 → 3~6초)** | 자료 5페이지 차단 사례 반영 |
| **Resume 필수** | 자료 차단 후 100건 손실 사례 |

---

## 14. 미결 사항 (지도교수 협의 필요)

1. **Yes24 한국 독자 서평 포함 여부** (§2.4) — 한·중 비교 연구로 확장?
2. **User-Agent 로테이션·프록시 사용 가부** — 윤리 vs 데이터 확보
3. **수집 가능 페이지 한도 도달 시 대응** — N < 200이면 분석 범위 조정?
4. **IRB 면제 vs 심의** — 공개 데이터 수집의 윤리심의 필요 수준
5. **익명화 데이터셋의 공개 범위** — 논문 부록·repository 공개 가능?

---

## 15. 참고 문서
- `references/web_scraping_tutorial_summary.md` — 자문 자료 요약
- `docs/01_research_design.md` — 연구 설계
- `docs/03_methodology_notes.md` — 재현성 기준
- `docs/04_ai_disclosure.md` — AI 활용 공시
- `code/01_preprocessing.py` — 다운스트림 전처리

### 참고 문헌
- 백선(2025), 「문체 번역 가능성 연구: 『채식주의자』 한·중 독자 서평의 NLP 비교·분석」

---

## 변경 이력
- v0.1 (2026-05-10): 초안.
- v1.0 (2026-05-10): 자문 자료(`web_scraping_tutorial.ipynb`) 반영, 도서 ID·셀렉터·헤더 확정. 차단 대응 강화. Yes24 미결 보존.
- v1.1 (2026-05-10): Yes24를 별도 PRD(`07_prd_yes24_crawler.md`)로 분리. §2.4 미결 사항 해소.
