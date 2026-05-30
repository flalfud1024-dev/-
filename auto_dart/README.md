# 국민연금 DART 공시 자동 알림 시스템 (카카오톡)

국민연금의 대량보유 공시를 자동으로 감지하고,  
매수 신호 발생 시 Claude AI가 종목을 분석해 **카카오톡**으로 알림을 보내는 시스템입니다.

## ⚙️ 동작 흐름

```
매일 오전 9시 자동 실행
↓
DART에서 국민연금 대량보유 공시 수집 (최근 7일)
↓
이전 지분율과 비교 → 매수 / 매도 / 유지 / 신규 판정
↓
카카오톡으로 지분변동 리포트 발송
↓
매수·신규 종목이 있으면 → Claude AI가 종목 분석 후 후속 메시지 발송
```

### 카카오톡 알림 예시

| 순서 | 내용 |
|------|------|
| 1번 메시지 | 📊 국민연금 지분변동 리포트 (매수/매도/유지/신규 요약) |
| 2번 메시지~ | 🔬 종목별 투자 리서치 (회사 개요, 실적, 업종 분위기, 기관 수급) |

---

## 🔑 필요한 것

| 항목 | 발급 방법 |
|------|----------|
| DART API 키 | [opendart.fss.or.kr](https://opendart.fss.or.kr) 회원가입 후 발급 |
| 카카오 REST API 키 | [developers.kakao.com](https://developers.kakao.com) 앱 생성 후 발급 |
| 카카오 Refresh Token | `kakao_auth.py` 실행 시 자동 저장 |
| Anthropic API 키 | [console.anthropic.com](https://console.anthropic.com) 에서 발급 |

---

## 🛠️ 설치 방법

### 1. 가상환경 생성 및 패키지 설치

```bash
cd auto_dart
python3 -m venv .venv
.venv/bin/pip install requests python-dotenv anthropic
```

### 2. 환경변수 설정

```bash
cp .env.example .env
# .env 파일을 열어 DART_API_KEY, KAKAO_REST_API_KEY, ANTHROPIC_API_KEY 입력
```

### 3. 카카오 앱 설정 (최초 1회)

[developers.kakao.com](https://developers.kakao.com) 에서:

1. **내 애플리케이션** → 앱 생성
2. **앱 설정 > 플랫폼** → Web 플랫폼 추가, 사이트 도메인: `http://localhost:8080`
3. **카카오 로그인** → 활성화 ON
4. **카카오 로그인 > Redirect URI** → `http://localhost:8080` 등록
5. **카카오 로그인 > 동의항목** → `카카오톡 메시지 전송` 활성화
6. **앱 키 > REST API 키**를 `.env`의 `KAKAO_REST_API_KEY`에 저장

### 4. 카카오 Refresh Token 발급 (최초 1회)

```bash
.venv/bin/python3 kakao_auth.py
```

브라우저에서 카카오 로그인 후 자동으로 `.env`에 `KAKAO_REFRESH_TOKEN`이 저장됩니다.

### 5. 수동 실행 테스트

```bash
.venv/bin/python3 main.py
```

정상이면 터미널에 아래와 같이 출력됩니다:

```
🔍 국민연금 공시 수집 시작...
  수집된 공시: N건
  신규 공시: N건
  리포트 발송 완료
✅ 완료
```

---

## ⏰ 자동 실행 설정 (macOS)

매일 오전 9시에 자동 실행되도록 등록합니다.

```bash
bash scheduler.sh
```

### 유용한 명령어

```bash
# 실행 로그 확인
tail -f /tmp/dart_tracker.log
# 에러 로그 확인
tail -f /tmp/dart_tracker_err.log
# 즉시 실행
launchctl start com.dart.pension.tracker
# 자동 실행 해제
launchctl unload ~/Library/LaunchAgents/com.dart.pension.tracker.plist
```

---

## 📁 파일 구조

```
auto_dart/
├── main.py           # 실행 진입점
├── dart_client.py    # DART API 호출
├── analyzer.py       # 지분변동 분석 (매수/매도 판정)
├── research_agent.py # Claude AI 종목 분석
├── notifier.py       # 카카오톡 발송
├── storage.py        # 처리된 공시 기록 관리
├── parser.py         # 공시 데이터 파싱
├── config.py         # 환경변수 로드
├── kakao_auth.py     # 카카오 OAuth 초기 설정 (최초 1회)
├── scheduler.sh      # macOS launchd 등록 스크립트
├── .env.example      # 환경변수 템플릿
├── .env              # 실제 API 키 (git에 올리지 말 것)
└── data/
    ├── seen.json             # 이미 처리한 공시 목록
    └── holding_history.json  # 종목별 이전 지분율 기록
```

---

## ⚠️ 주의사항

- `.env` 파일은 절대 git에 올리지 마세요. API 키가 포함되어 있습니다.
- 카카오 Refresh Token 유효기간은 **2개월**입니다. 만료 1개월 전에는 자동 갱신됩니다.
- 국민연금 대량보유 공시는 자주 나오지 않습니다 — 며칠간 알림이 없는 것은 정상입니다.
- Claude AI 분석은 **매수·신규 종목에만** 실행됩니다 (API 비용 절감).
- 이 시스템은 투자 참고용이며, 투자 판단은 본인 책임입니다.
