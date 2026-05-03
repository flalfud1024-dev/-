// OpenAI Whisper transcription proxy.
// Receives JSON { audio:base64, mimeType, language } and forwards a
// multipart/form-data request to OpenAI without any external dependency.

exports.handler = async (event) => {
  if (event.httpMethod !== "POST") {
    return { statusCode: 405, body: "Method Not Allowed" };
  }
  if (!process.env.OPENAI_API_KEY) {
    return { statusCode: 500, body: JSON.stringify({ error: "OPENAI_API_KEY not set" }) };
  }

  let payload;
  try { payload = JSON.parse(event.body || "{}"); }
  catch { return { statusCode: 400, body: JSON.stringify({ error: "invalid json" }) }; }

  const { audio, mimeType = "audio/mp4", language = "auto" } = payload;
  if (!audio) return { statusCode: 400, body: JSON.stringify({ error: "audio missing" }) };

  const buf = Buffer.from(audio, "base64");
  const ext = mimeType.includes("mp4") ? "mp4"
            : mimeType.includes("aac") ? "m4a"
            : mimeType.includes("webm") ? "webm"
            : mimeType.includes("ogg") ? "ogg" : "mp4";

  const boundary = "----irboundary" + Math.random().toString(36).slice(2);
  const CRLF = "\r\n";
  const parts = [];
  const push = (s) => parts.push(typeof s === "string" ? Buffer.from(s, "utf8") : s);

  push(`--${boundary}${CRLF}Content-Disposition: form-data; name="file"; filename="audio.${ext}"${CRLF}Content-Type: ${mimeType}${CRLF}${CRLF}`);
  push(buf);
  push(CRLF);

  push(`--${boundary}${CRLF}Content-Disposition: form-data; name="model"${CRLF}${CRLF}whisper-1${CRLF}`);
  push(`--${boundary}${CRLF}Content-Disposition: form-data; name="response_format"${CRLF}${CRLF}verbose_json${CRLF}`);

  if (language === "ko" || language === "zh") {
    push(`--${boundary}${CRLF}Content-Disposition: form-data; name="language"${CRLF}${CRLF}${language}${CRLF}`);
  }

  // 금융 IR 전문용어 힌트 — Whisper 인식 정확도 보정
  const prompt = "노무라증권 IR 한중 통역 미팅. 자주 등장하는 용어: AUM, ROE, IB, WM, ECM, DCM, PI, ELS, DLS, IR, NPS, MSCI, Repo, RP, FCY, CB, 판다채권, 역외 위안화, 역내 위안화, CNH, CNY, 조달금리, 익스포저, 자기자본, 순자본비율, 배당성향, 자본배분, 크로스보더, 주관사, 로드쇼, 북빌딩, 트랜치, 스프레드, 만기. 中文常用词: 投资者关系, 投资银行, 财富管理, 股权资本市场, 债务资本市场, 自营投资, 股本回报率, 熊猫债券, 离岸人民币, 在岸人民币, 融资成本, 风险敞口, 资本配置, 主承销商, 簿记建档, 路演, 跨境交易, 净资本比率, 股息支付率.";
  push(`--${boundary}${CRLF}Content-Disposition: form-data; name="prompt"${CRLF}${CRLF}${prompt}${CRLF}`);

  push(`--${boundary}--${CRLF}`);
  const body = Buffer.concat(parts);

  try {
    const res = await fetch("https://api.openai.com/v1/audio/transcriptions", {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${process.env.OPENAI_API_KEY}`,
        "Content-Type": `multipart/form-data; boundary=${boundary}`,
        "Content-Length": String(body.length),
      },
      body,
    });
    const txt = await res.text();
    if (!res.ok) {
      return { statusCode: res.status, body: JSON.stringify({ error: txt }) };
    }
    const data = JSON.parse(txt);
    return {
      statusCode: 200,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: (data.text || "").trim(), language: data.language || language }),
    };
  } catch (e) {
    return { statusCode: 500, body: JSON.stringify({ error: String(e.message || e) }) };
  }
};
