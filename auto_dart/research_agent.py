import anthropic
from config import ANTHROPIC_API_KEY
from analyzer import AnalysisResult

_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def analyze_stock(result: AnalysisResult) -> str:
    corp_name = result.disclosure.corp_name
    action = result.action
    curr = result.curr_ratio
    prev = result.prev_ratio

    if prev is not None:
        ratio_desc = f"기존 {prev:.2f}% → 현재 {curr:.2f}% ({curr - prev:+.2f}%p)"
    else:
        ratio_desc = f"신규 보유 {curr:.2f}%"

    prompt = f"""국민연금이 {corp_name} 주식을 {action}했습니다.
보유비율: {ratio_desc}

아래 5가지 항목을 각각 2~3문장으로 간결하게 분석해주세요.
1. 회사 개요 및 주요 사업
2. 최근 실적 및 재무 상태
3. 업종 분위기 및 시장 위치
4. 기관 수급 관점 해석 (국민연금 {action}의 의미)
5. 종합 투자 판단 (단기/중장기 전망)

한국어로 답변해주세요."""

    message = _client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    body = message.content[0].text
    return f"🔬 {corp_name} 투자 리서치\n국민연금 {action} ({ratio_desc})\n\n{body}"
