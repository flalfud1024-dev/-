# crawler_common

박사학위논문 데이터 수집의 **공통 유틸리티 모듈**.
`crawler_douban`, `crawler_yes24`가 공유한다.

## 모듈 (STEP 2에서 구현 예정)

| 모듈 | 책임 |
|------|------|
| `anonymizer.py` | SHA-256 + salt 사용자 ID 해싱 |
| `logger.py` | 통합 로깅 (logging 모듈 래퍼) |
| `state.py` | resume용 상태 관리 (`state.json`) |
| `deduper.py` | review_id + Levenshtein fuzzy 중복 제거 |
| `config.py` | YAML 설정 + .env 로드 |

## 환경 설정

```bash
# 1. 의존성 설치
pip install -r crawler_common/requirements.txt

# 2. 환경변수 설정
cp crawler_common/.env.example .env
# 후 .env 파일을 편집하여 실제 값 입력

# 3. 익명화 salt 생성 예시
python -c "import secrets; print(secrets.token_hex(32))"
```

## 디렉토리 구조

```
crawler_common/
├── README.md
├── requirements.txt           # 두 크롤러 공통 의존성
├── .env.example               # 환경변수 템플릿
├── (STEP 2에서 추가) anonymizer.py / logger.py / state.py / deduper.py / config.py
└── tests/
    └── (STEP 2에서 추가)
```

## 실행 환경 가정

- Python 3.10.x
- Linux/macOS (Yes24 Selenium은 Chrome 필요)
- `RANDOM_SEED = 42` 전역 고정 (재현성)
