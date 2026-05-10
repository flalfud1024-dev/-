# crawler_douban

豆瓣 (중국) 독자 리뷰 수집 크롤러.
PRD: [`docs/06_prd_douban_crawler.md`](../docs/06_prd_douban_crawler.md)

## 수집 대상 (PRD §2.1)

| 번역본 | 도서 ID | 출판사 |
|--------|---------|--------|
| 후추통 2021 (간체) | `35534519` | 四川文艺出版社 |
| 천일 2016 (번체) | `26735623` | 漫遊者文化 |
| 천일 2013 (간체) | `24847418` | 重庆出版社 |

## 사용법 (STEP 6 완료 후)

```bash
# 단일 번역본 수집
python crawler_douban/crawl.py --version huchutong_2021

# 전체 수집
python crawler_douban/crawl.py --version all

# 차단 후 재개
python crawler_douban/crawl.py --version tianyi_2013 --resume
```

## 디렉토리 구조 (단계별 구축)

```
crawler_douban/
├── README.md
├── config.yaml                # ✅ STEP 1
├── (STEP 3) fetcher.py
├── (STEP 4) parser_comments.py
├── (STEP 5) parser_reviews.py
├── (STEP 6) crawl.py
├── tests/
│   ├── fixtures/              # ✅ STEP 1 (빈 디렉토리)
│   └── (STEP 4-5) test_parser_*.py
└── data/                       # 자동 생성, .gitignore
    ├── raw/                    # CSV 출력
    ├── raw/_logs/
    ├── raw/_snapshots/
    └── raw/_state/             # resume 상태
```

## 기술 스택

- `requests` + `BeautifulSoup4` (정적 페이지)
- `tenacity` (재시도)
- `tqdm` (진행률)

## 윤리 정책

- robots.txt 준수
- 페이지당 3~6초 무작위 지연 (config로 조정 가능)
- User-Agent 단일 고정 (로테이션 미사용)
- 403 발생 시 즉시 중단 + state.json에 페이지 저장
- 사용자 ID는 SHA-256 + salt로 익명화
