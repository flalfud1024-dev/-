# crawler_yes24

Yes24 (한국) 독자 리뷰 수집 크롤러 — **보조 baseline용**.
PRD: [`docs/07_prd_yes24_crawler.md`](../docs/07_prd_yes24_crawler.md)

## 수집 대상 (PRD §2.1)

| 도서 | 상품 ID |
|------|---------|
| 한강 『채식주의자』 (창비) | `108422348` |

## 사용법 (STEP 9 완료 후)

```bash
# 기본 수집
python crawler_yes24/crawl.py --product 108422348

# 노벨상 전후 분리 분석
python crawler_yes24/crawl.py --product 108422348 --split-nobel

# 재개
python crawler_yes24/crawl.py --product 108422348 --resume
```

## 디렉토리 구조

```
crawler_yes24/
├── README.md
├── config.yaml                # ✅ STEP 1
├── (STEP 7) driver_factory.py
├── (STEP 7) navigator.py
├── (STEP 8) parser.py
├── (STEP 9) crawl.py
├── tests/
│   ├── fixtures/              # ✅ STEP 1 (빈 디렉토리)
│   └── (STEP 8) test_parser.py
└── data/                       # .gitignore
```

## 기술 스택

- `Selenium` + `webdriver-manager` (동적 페이지)
- `BeautifulSoup4` (page_source 파싱)
- Chrome 헤드리스

## 노벨상 효과 분리

2024-10-10(노벨문학상 발표일)을 기준으로 리뷰에 `is_post_nobel` 플래그 부여.
수상 효과로 인한 리뷰 양상 급변을 분석에서 분리할 수 있도록 함.

## 환경 요구

- Chrome 또는 Chromium 설치
- Linux 환경에서는 `--no-sandbox`, `--disable-dev-shm-usage` 필수 (config로 적용)
