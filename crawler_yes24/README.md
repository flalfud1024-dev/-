# Yes24 크롤러

한강 『채식주의자』 한국어 원본의 Yes24 리뷰 수집기.
**박사학위논문의 보조 baseline 데이터** 수집용.

## 설치

```bash
# 저장소 루트에서
pip install -r requirements.txt

# 환경변수 (해시 salt)
cp .env.example .env
# .env 편집

# Chrome 설치 필요 (없으면 설치)
#   Ubuntu/Debian: sudo apt install chromium-browser
#   Mac:           brew install --cask google-chrome
# ChromeDriver는 webdriver-manager가 자동 다운로드
```

## 사용법

```bash
cd crawler_yes24

# 기본 (상품 ID만 주기)
python crawl.py 108422348

# 페이지·정렬 지정
python crawl.py 108422348 --max-pages 20 --sort popular

# URL로도 가능
python crawl.py --url https://www.yes24.com/Product/Goods/108422348

# 디버깅 (브라우저 창 보기)
python crawl.py 108422348 --no-headless

# 도움말
python crawl.py --help
```

## 인자 정리

| 인자 | 설명 | 기본값 |
|------|------|--------|
| `product_id` | Yes24 상품 ID | (필수) |
| `--url` | 전체 URL | - |
| `--max-pages` | 최대 페이지 수 | 10 |
| `--sort` | `popular`(공감순) / `latest`(최신순) | popular |
| `--date-from` / `--date-to` | 날짜 필터 (YYYY-MM-DD) | - |
| `--out-dir` | 출력 폴더 | `./data` |
| `--no-headless` | 브라우저 창 표시 | (꺼짐) |

## 본 학위논문 수집 대상

| 도서 | 상품 ID |
|------|---------|
| 한강 『채식주의자』 (창비) | `108422348` |

## 출력 파일

```
data/
├── yes24_108422348_20260510_140532.csv
├── yes24_108422348_20260510_140532.log
└── _snapshots/108422348/
    └── page_001.html ...
```

### CSV 컬럼

| 컬럼 | 설명 |
|------|------|
| `product_id` | 상품 ID |
| `user_id_hash` | SHA-256 익명화 |
| `rating` | 별점 |
| `date` | 작성일 |
| `helpful_votes` | 공감 수 |
| **`is_post_nobel`** | 2024-10-10 이후 작성 여부 (`True`/`False`) |
| `text` | 본문 |
| `page` | 페이지 번호 |
| `crawl_timestamp` | 수집 시각 (UTC) |

## ⚠️ 셀렉터 주의사항

Yes24 페이지 구조는 자주 바뀝니다.

본 크롤러의 `parse_reviews()` 함수는 다음 후보 셀렉터를 순차 시도합니다:
- 리뷰 컨테이너: `div.reviewInfoGrp`, `li.reviewInfoItem`, `div.review_cont` 등
- 작성자/별점/날짜/본문/공감 수도 각각 여러 후보 시도

**실제 페이지 구조와 다르면 `parse_reviews()` 내부 셀렉터를 직접 수정**해야 합니다.
스냅샷 HTML(`_snapshots/`)로 사후 검증·재파싱 가능합니다.

## 노벨상 효과 분리

`is_post_nobel` 플래그로 2024-10-10(한강 노벨문학상 발표) 전후 리뷰를 분리 분석할 수 있도록 했습니다.

논문에서는 두 시기를 별도 코퍼스로 다뤄 수상 효과로 인한 리뷰 양상 급변을 분석에서 분리할 수 있습니다.

## 논문 인용

```
부록 5: 데이터 수집 코드
저장소: https://github.com/{사용자}/{레포}
사용 커밋: {commit hash}
실행 명령: python crawler_yes24/crawl.py 108422348 --max-pages 20
```
