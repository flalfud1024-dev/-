# IR 통역 보조 (노무라 한↔중)

순차통역 현장에서 PC 줌 통화 옆에 아이폰을 두고, 발화 단락이 끝날 때마다
**Whisper 전사 → Claude 번역**을 자동으로 받아보기 위한 1‑페이지 웹앱입니다.

## 기능

- 🎙 한국어/중국어 음성 자동 인식 (OpenAI Whisper, 금융 IR 용어 프롬프트 힌트 내장)
- 🔁 한↔중 자동 양방향 번역 (Claude Haiku, IR 컨텍스트 시스템 프롬프트)
- 🟡 IR 전문용어 자동 하이라이트 + 매칭 칩
- 📜 단락별 카드가 누적, 녹음을 멈춰도 사라지지 않음 (localStorage)
- 💱 억원 ↔ 中文 단위 변환기
- 🔍 80+ IR 용어 검색 (탭하면 中文 자동 복사)

## 폴더 구조

```
ir-interpreter/
├── index.html                       # 단일 페이지 앱
├── netlify.toml                     # /api/* → functions 리다이렉트
├── netlify/functions/
│   ├── transcribe.js                # Whisper 프록시 (multipart 자체 구성)
│   └── translate.js                 # Claude Haiku 프록시
└── README.md
```

## 배포 (Netlify Drop · 5분)

1. `ir-interpreter` 폴더 **전체**를 PC에서 ZIP 압축 (또는 폴더째 드래그)
2. <https://app.netlify.com/drop> 에서 폴더(또는 ZIP)를 드롭
3. 사이트 생성 후 **Site configuration → Environment variables** 에서 두 개 등록:
   - `OPENAI_API_KEY` = `sk-...` (Whisper)
   - `ANTHROPIC_API_KEY` = `sk-ant-...` (Claude)
4. **Deploys → Trigger deploy → Clear cache and deploy site**
5. 생성된 `https://xxxx.netlify.app` 주소를 **아이폰 Safari**로 열기
6. 처음 녹음 시 마이크 권한 허용

> Netlify Functions가 Node 18+에서 `fetch` 글로벌을 사용합니다.
> 추가 npm 의존성은 없으며 `package.json` 도 필요 없습니다.

## 사용 흐름

1. 상단에서 발화 언어 선택 (자동/🇰🇷/🇨🇳). 자동도 잘 작동하지만,
   화자가 정해져 있으면 명시하는 게 정확도가 더 좋습니다.
2. **🎙 녹음 시작** → 한 발화(한 단락)가 끝나면 **⏹ 중지**
3. 카드가 즉시 추가되고, 전사 → 번역이 차례로 채워집니다
4. 다음 단락도 같은 방식으로. 카드는 계속 위로 쌓이고 마지막 카드는
   파란 테두리로 강조됩니다 (참조용)
5. **📋 전체 복사** 로 회의 후 로그 백업, **🗑** 으로 초기화

## 비용 가이드

- Whisper: 분당 약 $0.006 (1시간 미팅 ≈ $0.36)
- Claude Haiku: 한 단락 번역당 약 $0.001 미만

## 제한 / 트러블슈팅

| 증상 | 원인 / 해결 |
|---|---|
| 마이크 거부 (`not-allowed`) | iOS: 설정 → Safari → 마이크 = 허용. 사이트 별 권한은 주소창의 `AA` → 웹사이트 설정. |
| 녹음 후 `OPENAI_API_KEY not set` | Netlify 환경변수 등록 후 **Trigger deploy** 안 한 경우. |
| `Load failed` / 번역 실패 | 동일하게 `ANTHROPIC_API_KEY` 등록 + 재배포 필요. |
| 한국어인데 中文으로 인식 | 발화 언어를 `🇰🇷 한국어` 로 고정. |
| 단락이 너무 잘게/길게 끊김 | 순차통역 전제이므로 사용자가 발화 사이에 직접 ⏹/🎙 토글. |

## 기록

이 도구의 용어 사전과 시스템 프롬프트는 노무라증권 한중 IR 미팅 통역 준비
세션의 자료를 기반으로 구성되었습니다 (판다채권·역내·역외 위안화 중심,
재무제표·조달금리 개념까지 커버).
