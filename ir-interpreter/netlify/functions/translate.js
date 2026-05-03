// Claude translation proxy. Receives { text, source, target } and returns
// { translation }. Uses Claude Haiku for speed in a live interpreting setting.

exports.handler = async (event) => {
  if (event.httpMethod !== "POST") {
    return { statusCode: 405, body: "Method Not Allowed" };
  }
  if (!process.env.ANTHROPIC_API_KEY) {
    return { statusCode: 500, body: JSON.stringify({ error: "ANTHROPIC_API_KEY not set" }) };
  }

  let payload;
  try { payload = JSON.parse(event.body || "{}"); }
  catch { return { statusCode: 400, body: JSON.stringify({ error: "invalid json" }) }; }

  const { text, source = "ko", target = "zh" } = payload;
  if (!text || !text.trim()) {
    return { statusCode: 200, body: JSON.stringify({ translation: "" }) };
  }

  const dir = source === "ko" ? "한국어 → 中文(简体)" : "中文 → 한국어";

  const system = `당신은 노무라증권 IR(Investor Relations) 미팅의 한↔중 순차 통역사입니다.
방향: ${dir}.

원칙:
1) 금융·자본시장 전문용어는 업계 표준 대응어를 사용한다.
   - AUM=管理资产规模, ROE=股本回报率, IB=投资银行业务, WM=财富管理,
     ECM=股权资本市场, DCM=债务资本市场, PI=自营投资,
     판다채권=熊猫债券, 역외 위안화=离岸人民币(CNH), 역내 위안화=在岸人民币(CNY),
     조달금리=融资成本, 익스포저=风险敞口, 자본배분=资本配置,
     순자본비율=净资本比率, 배당성향=股息支付率, 자기자본=自有资本/股东权益,
     주관사=主承销商, 로드쇼=路演, 북빌딩=簿记建档, 크로스보더=跨境.
2) 금액 단위는 절대 임의로 바꾸지 않는다.
   - 한국어 "1조 원" ↔ 中文 "1万亿韩元" (절대 "1兆韩元" 금지).
   - "1억 원" ↔ "1亿韩元", "1천억 원" ↔ "1000亿韩元".
3) 회사명·인명·약어(IR, IPO, ELS, DLS, NPS, MSCI, DJSI 등)는 원문 표기를 유지한다.
4) 통역 결과만 출력한다. 설명·주석·따옴표·"译文:" 같은 라벨 금지.
5) 발화가 불완전하거나 단어 단편이면 들린 그대로 자연스럽게 다듬어 옮긴다.`;

  try {
    const res = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: {
        "x-api-key": process.env.ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
      },
      body: JSON.stringify({
        model: "claude-haiku-4-5-20251001",
        max_tokens: 1024,
        system,
        messages: [{ role: "user", content: text }],
      }),
    });
    const txt = await res.text();
    if (!res.ok) {
      return { statusCode: res.status, body: JSON.stringify({ error: txt }) };
    }
    const data = JSON.parse(txt);
    const translation = (data.content && data.content[0] && data.content[0].text || "").trim();
    return {
      statusCode: 200,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ translation }),
    };
  } catch (e) {
    return { statusCode: 500, body: JSON.stringify({ error: String(e.message || e) }) };
  }
};
