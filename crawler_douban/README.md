# 豆瓣 크롤러

한강 『채식주의자』 중국어 번역본 독자 단평 수집기.

## 설치

```bash
# 저장소 루트에서
pip install -r requirements.txt

# 환경변수 설정
cp .env.example .env
# .env 열어서 ANONYMIZATION_SALT 값을 채움
# salt 생성: python -c "import secrets; print(secrets.token_hex(32))"
```

## 사용법

```bash
cd crawler_douban

# 가장 단순: 도서 ID만 주기
python crawl.py 35534519

# 정렬·페이지 수·날짜 필터
python crawl.py 35534519 --max-pages 20 --sort score \
                        --date-from 2024-01-01 --date-to 2024-12-31

# 전체 URL로도 가능
python crawl.py --url https://book.douban.com/subject/35534519/

# 도움말
python crawl.py --help
```

## 인자 정리

| 인자 | 설명 | 기본값 |
|------|------|--------|
| `book_id` | 豆瓣 도서 ID | (필수) |
| `--url` | 전체 URL (book_id 대신) | - |
| `--max-pages` | 최대 페이지 수 (페이지당 20건) | 10 |
| `--sort` | `score`(공감순) / `new` / `time` | score |
| `--status` | `P` 읽음 / `F` 읽는중 / `W` 읽고싶음 | P |
| `--date-from` | 시작일 (YYYY-MM-DD) | - |
| `--date-to` | 종료일 (YYYY-MM-DD) | - |
| `--out-dir` | 출력 폴더 | `./data` |

## 본 학위논문 수집 대상 도서 ID

| 번역본 | 도서 ID |
|--------|---------|
| 후추통 2021 (간체) | `35534519` |
| 천일 2016 (번체, 타이완) | `26735623` |
| 천일 2013 (간체, 본토) | `24847418` |

## 출력 파일

```
data/
├── douban_35534519_20260510_140532.csv     # 수집 데이터
├── douban_35534519_20260510_140532.log     # 실행 로그 (재현성 증거)
└── _snapshots/35534519/
    ├── page_001.html                        # 원본 HTML (재파싱·검증용)
    ├── page_002.html
    └── ...
```

### CSV 컬럼

| 컬럼 | 설명 |
|------|------|
| `review_id` | 豆瓣 내부 ID |
| `book_id` | 도서 ID |
| `user_id_hash` | SHA-256(username + salt) — **익명화됨** |
| `rating` | 1~5 별점 (없으면 비어있음) |
| `date` | 작성일 |
| `likes` | 공감(유용) 수 |
| `text` | 단평 본문 |
| `page` | 수집된 페이지 번호 |
| `crawl_timestamp` | 수집 시각 (ISO 8601, UTC) |

## 윤리·재현성 정책

- **익명화**: 사용자명은 환경변수 salt를 사용한 SHA-256 해시로 변환
- **요청 간격**: 페이지당 3~6초 무작위 지연 (`random_seed=42`로 패턴 재현 가능)
- **User-Agent**: 일반 브라우저 식별자 단일 고정, 로테이션 미사용
- **403 대응**: 재시도 3회 후 즉시 중단 + 그때까지 수집분 보존
- **스냅샷**: 모든 페이지 원본 HTML 저장 → 사후 검증·재파싱 가능
- **로그**: 모든 요청·응답을 별도 파일에 기록

## 차단 발생 시

豆瓣은 anti-scraping이 강력합니다. 5~10페이지 후 403이 흔합니다.

- 수집된 만큼은 CSV에 이미 저장됨 (flush per page)
- 24시간 이상 휴지 후 다시 시도
- 그래도 차단되면 다른 IP / 시간대 시도
- IP 우회는 **사용하지 않음** (윤리 정책)

## 논문 인용

본 크롤러는 박사학위논문 부록에 **GitHub 링크 + commit hash**로 인용됩니다.

```
부록 5: 데이터 수집 코드
저장소: https://github.com/{사용자}/{레포}
사용 커밋: {commit hash}
실행 명령: python crawler_douban/crawl.py 35534519 --max-pages 20
```
