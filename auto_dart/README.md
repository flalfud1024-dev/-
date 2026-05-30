# 국민연금 DART 공시 자동 알림 시스템 (이메일)

국민연금의 대량보유 공시를 자동으로 감지하고,  
매수 신호 발생 시 Claude AI가 종목을 분석해 **Gmail**로 알림을 보내는 시스템입니다.

## ⚙️ 동작 흐름

```
매일 오전 9시 자동 실행
↓
DART에서 국민연금 대량보유 공시 수집 (최근 7일)
↓
이전 지분율과 비교 → 매수 / 매도 / 유지 / 신규 판정
↓
이메일로 지분변동 리포트 발송
↓
매수·신규 종목이 있으면 → Claude AI가 종목 분석 후 후속 메시지 발송
```

---

## 🔑 필요한 것 (3가지)

| 항목 | 발급 방법 |
|------|----------|
| DART API 키 | [opendart.fss.or.kr](https://opendart.fss.or.kr) 회원가입 후 발급 |
| Gmail 앱 비밀번호 | 구글 계정 보안 설정에서 발급 (5분) |
| Anthropic API 키 | [console.anthropic.com](https://console.anthropic.com) 에서 발급 |

---

## 🛠️ 설치 방법

### 1. 가상환경 생성 및 패키지 설치

```bash
cd auto_dart
python3 -m venv .venv
.venv/bin/pip install requests python-dotenv anthropic
```

### 2. Gmail 앱 비밀번호 발급

1. [myaccount.google.com/security](https://myaccount.google.com/security) 접속
2. **2단계 인증** 활성화 (이미 되어 있으면 건너뜀)
3. 검색창에 **"앱 비밀번호"** 검색 → 앱 이름 입력 후 생성
4. 표시되는 **16자리 비밀번호** 복사

### 3. 환경변수 설정

```bash
cp .env.example .env
```

`.env` 파일을 열어 아래 항목 입력:

```
DART_API_KEY=...
GMAIL_ADDRESS=yourname@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
ANTHROPIC_API_KEY=...
```

`NOTIFY_EMAIL`은 비워두면 본인 Gmail로 발송됩니다.

### 4. 수동 실행 테스트

```bash
.venv/bin/python3 main.py
```

---

## ⏰ 자동 실행 설정 (macOS)

```bash
bash scheduler.sh
```

### 유용한 명령어

```bash
tail -f /tmp/dart_tracker.log       # 실행 로그
tail -f /tmp/dart_tracker_err.log   # 에러 로그
launchctl start com.dart.pension.tracker   # 즉시 실행
launchctl unload ~/Library/LaunchAgents/com.dart.pension.tracker.plist  # 해제
```

---

## 📁 파일 구조

```
auto_dart/
├── main.py           # 실행 진입점
├── dart_client.py    # DART API 호출
├── analyzer.py       # 지분변동 분석 (매수/매도 판정)
├── research_agent.py # Claude AI 종목 분석
├── notifier.py       # Gmail 발송
├── storage.py        # 처리된 공시 기록 관리
├── parser.py         # 공시 데이터 파싱
├── config.py         # 환경변수 로드
├── scheduler.sh      # macOS launchd 등록 스크립트
├── .env.example      # 환경변수 템플릿
├── .env              # 실제 API 키 (git에 올리지 말 것)
└── data/
    ├── seen.json             # 이미 처리한 공시 목록
    └── holding_history.json  # 종목별 이전 지분율 기록
```

---

## ⚠️ 주의사항

- `.env` 파일은 절대 git에 올리지 마세요.
- Gmail 앱 비밀번호는 일반 로그인 비밀번호와 다릅니다.
- 국민연금 대량보유 공시는 자주 나오지 않습니다 — 며칠간 알림이 없는 것은 정상입니다.
- Claude AI 분석은 **매수·신규 종목에만** 실행됩니다 (API 비용 절감).
- 이 시스템은 투자 참고용이며, 투자 판단은 본인 책임입니다.
