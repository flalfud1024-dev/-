"""
Gmail SMTP를 이용한 이메일 알림 모듈.

사전 준비:
  Gmail 계정 설정 > 보안 > 2단계 인증 ON 후
  '앱 비밀번호' 발급 → .env의 GMAIL_APP_PASSWORD에 저장
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import GMAIL_ADDRESS, GMAIL_APP_PASSWORD, NOTIFY_EMAIL

_SMTP_HOST = "smtp.gmail.com"
_SMTP_PORT = 587


def send_message(text: str, dart_url: str = "") -> None:
    body = text
    if dart_url:
        body += f"\n\n📎 DART 원문: {dart_url}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = _extract_subject(text)
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = NOTIFY_EMAIL

    # 평문 + HTML 두 가지 형식
    plain = MIMEText(body, "plain", "utf-8")
    html_body = body.replace("\n", "<br>")
    if dart_url:
        html_body = html_body.replace(
            dart_url, f'<a href="{dart_url}">{dart_url}</a>'
        )
    html = MIMEText(f"<pre style='font-family:sans-serif'>{html_body}</pre>", "html", "utf-8")

    msg.attach(plain)
    msg.attach(html)

    with smtplib.SMTP(_SMTP_HOST, _SMTP_PORT) as smtp:
        smtp.starttls()
        smtp.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        smtp.sendmail(GMAIL_ADDRESS, NOTIFY_EMAIL, msg.as_string())


def _extract_subject(text: str) -> str:
    first_line = text.strip().split("\n")[0]
    # 이모지 포함 첫 줄을 제목으로 사용, 60자 초과 시 자름
    return first_line[:60]
