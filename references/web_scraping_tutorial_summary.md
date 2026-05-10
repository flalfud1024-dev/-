# 자문 자료: web_scraping_tutorial.ipynb (요약 보존본)

> **출처**: 데이터사이언스 전공 ○○○ 선생님 과외 자료
> **수령일**: 2026-05-10
> **원본**: Google Colab Notebook (web_scraping_tutorial.ipynb)
> **참고 논문**: 백선(2025), 「문체 번역 가능성 연구: 『채식주의자』 한·중 독자 서평의 NLP 비교·분석」

본 문서는 자문 자료의 핵심 결정사항·재사용 가능한 패턴만 발췌·정리한 것이다. 본 학위논문 코드는 본 자료를 기반으로 재현성·윤리·구조화를 강화하여 재구성한다.

---

## 1. 확정 사항

### 1.1 豆瓣 도서 ID
| 번역본 | 도서 ID | URL 패턴 |
|--------|---------|----------|
| 후추통 2021 (간체) | `35534519` | `https://book.douban.com/subject/35534519/` |
| 천일 2016 (번체, 타이완) | `26735623` | `https://book.douban.com/subject/26735623/` |
| 천일 2013 (간체, 본토) | `24847418` | `https://book.douban.com/subject/24847418/` |

### 1.2 기술 스택
| 사이트 | 라이브러리 | 근거 |
|--------|-----------|------|
| 豆瓣 (단평·서평) | `requests` + `BeautifulSoup4` (lxml) | 정적 페이지 |
| Yes24 (한국 리뷰) | `Selenium` + `webdriver_manager` | 동적 페이지 |

### 1.3 HTTP 헤더 표준
```python
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,ko;q=0.7',
    'Referer': 'https://book.douban.com/',
}
```

### 1.4 페이지네이션
- 단평: `https://book.douban.com/subject/{book_id}/comments/?start={start}&limit=20&status={status}&sort=score`
- 서평: `https://book.douban.com/subject/{book_id}/reviews?start={start}`
- `start`는 0, 20, 40, ... (limit=20 단위)
- `status`: `P`(읽음) / `F`(읽는 중) / `W`(읽고 싶음)

### 1.5 파싱 셀렉터 (단평)
| 필드 | CSS 셀렉터 |
|------|------------|
| 단평 항목 | `li.comment-item` |
| 사용자명 | `span.comment-info a` |
| 평점 | `span.comment-info span[class*="rating"]` → `allstar{N}0` 클래스에서 N 추출 |
| 날짜 | `span.comment-info span.comment-time` |
| 본문 | `span.short` |
| 좋아요 | `span.vote-count` |

### 1.6 파싱 셀렉터 (장평)
| 필드 | CSS 셀렉터 |
|------|------------|
| 리뷰 항목 | `div.review-item` |
| 제목 | `h2 a` |
| 작성자 | `header.main-hd a.name` |
| 평점 | `span[class*="rating"]` → `allstar` 클래스 |
| 본문(요약) | `div.short-content` |

### 1.7 평점 변환
```python
# 클래스명 'allstar50' → 5점, 'allstar40' → 4점
rating = int(rating_class.replace('allstar', '')) // 10
```

---

## 2. 자료에서 드러난 결정적 위험

### 2.1 IP 차단 (관측된 실패)
> **튜토리얼 실측 결과**: 페이지 1~5(100건)까지는 정상 수집되었으나, **6페이지부터 403 Forbidden 연속 발생, 재시도 모두 실패**.
>
> 적용된 지연: `random.uniform(2, 4)` 초

**해석**:
- 단순 지연만으로는 100건 수집 후 차단 발생 → 본 학위논문 목표 N≥200/번역본 충족 불가
- Colab 공용 IP가 이미 차단 누적 상태였을 가능성
- 더우반의 anti-scraping이 매우 강력 → 별도 전략 필수

### 2.2 자료가 제시한 우회 방법 (PRD에서 윤리적 검토 필요)
```python
# 자료 부록 A
user_agents = [...]  # User-Agent 로테이션
proxies = {...}      # 프록시 사용
time.sleep(random.uniform(3, 7))  # 더 긴 지연
```

> ⚠️ **윤리적 판단 필요**: User-Agent 로테이션·프록시는 차단 우회로 분류될 수 있음. 학술 연구 정당성 vs 사이트 ToS 위반 우려를 지도교수·자문 선생님과 논의 후 결정.

---

## 3. 자료에서 새롭게 등장한 사항 (스코프 결정 필요)

### 3.1 Yes24 한국 독자 서평
- 자료에 Yes24 리뷰 수집 코드 포함 (Selenium 기반)
- 상품 ID 예시: `108422348`
- 참고 논문(백선 2025)이 **한·중 독자 서평 NLP 비교 연구**임

> ❓ **결정 필요**: 본 학위논문이 중국 독자만 대상인지, 한국 독자도 포함하는 한·중 비교 연구로 확장할지?

---

## 4. 자료의 재현성·구조 개선 필요 항목

자료 코드를 학위논문 부록으로 그대로 사용하기에 부족한 부분:

| 항목 | 자료 상태 | 학위논문에 필요한 보강 |
|------|-----------|----------------------|
| 도서 ID 관리 | 코드 내 하드코딩 | `config.yaml`로 분리 |
| HTML 스냅샷 | 미저장 | 검증·재파싱 위한 저장 의무화 |
| 로깅 | print만 사용 | `logging` 모듈 + 파일 기록 |
| 익명화 | 없음 | SHA-256 + salt 해싱 필수 |
| 중복 제거 | 없음 | review_id + fuzzy matching |
| 단위테스트 | 없음 | parser.py 픽스처 기반 테스트 |
| Resume 기능 | 없음 | 차단 발생 후 재개 가능해야 함 |
| 수집 메타데이터 | 없음 | 시각·환경·시드 기록 |

---

## 5. 본 학위논문 코드와의 관계

본 자료는 **방법론적 출발점·검증된 셀렉터 소스**로 활용한다.
본 학위논문 크롤러는 본 자료의 실용 패턴을 차용하되,
재현성·윤리·테스트 가능성을 강화하여 재구성한다.

논문 부록 5에는 다음을 명시:
> "본 연구의 데이터 수집 코드는 데이터사이언스 자문 선생님이 제공한 튜토리얼 자료(web_scraping_tutorial.ipynb, 2026)의 셀렉터 및 페이지네이션 패턴을 토대로, 연구자가 재현성과 익명화 처리를 강화하여 재구현하였다."
