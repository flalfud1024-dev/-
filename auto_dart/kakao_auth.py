#!/usr/bin/env python3
"""
카카오 OAuth 초기 설정 도우미 (최초 1회만 실행)

실행 전 카카오 개발자 콘솔(developers.kakao.com) 에서:
  1. 내 애플리케이션 > 앱 설정 > 플랫폼 > Web 플랫폼 등록
     - 사이트 도메인: http://localhost:8080
  2. 카카오 로그인 > 활성화 ON
  3. 카카오 로그인 > Redirect URI 등록: http://localhost:8080
  4. 카카오 로그인 > 동의항목 > '카카오톡 메시지 전송' 선택(필수 또는 선택 동의)
  5. 앱 키 > REST API 키를 .env의 KAKAO_REST_API_KEY에 저장
"""

import os
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import requests
from dotenv import load_dotenv, set_key

_ENV_FILE = Path(__file__).parent / ".env"
load_dotenv(_ENV_FILE)

_AUTH_URL = "https://kauth.kakao.com/oauth/authorize"
_TOKEN_URL = "https://kauth.kakao.com/oauth/token"
_REDIRECT_URI = "http://localhost:8080"

_code_holder: dict[str, str | None] = {"code": None}


class _CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        _code_holder["code"] = (params.get("code") or [None])[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(
            "<html><body><h2>✅ 인증 완료! 이 창을 닫고 터미널로 돌아오세요.</h2></body></html>".encode()
        )

    def log_message(self, *args) -> None:  # suppress server logs
        pass


def main() -> None:
    rest_api_key = os.environ.get("KAKAO_REST_API_KEY", "").strip()
    if not rest_api_key:
        print("❌ .env에 KAKAO_REST_API_KEY가 없습니다. 먼저 .env를 설정하세요.")
        return

    auth_url = (
        _AUTH_URL
        + "?"
        + urllib.parse.urlencode({
            "client_id": rest_api_key,
            "redirect_uri": _REDIRECT_URI,
            "response_type": "code",
            "scope": "talk_message",
        })
    )

    print(f"브라우저에서 카카오 로그인 페이지를 엽니다...")
    print(f"(자동으로 열리지 않으면 아래 URL을 복사하세요)\n{auth_url}\n")
    webbrowser.open(auth_url)

    print("로그인 후 자동으로 토큰을 발급합니다. 잠시 기다려주세요...")
    server = HTTPServer(("localhost", 8080), _CallbackHandler)
    server.handle_request()

    code = _code_holder["code"]
    if not code:
        print("❌ 인증 코드를 받지 못했습니다. 다시 시도해주세요.")
        return

    resp = requests.post(
        _TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "client_id": rest_api_key,
            "redirect_uri": _REDIRECT_URI,
            "code": code,
        },
        timeout=10,
    )
    resp.raise_for_status()
    token_data = resp.json()

    refresh_token = token_data.get("refresh_token")
    if not refresh_token:
        print(f"❌ refresh_token 발급 실패: {token_data}")
        return

    set_key(str(_ENV_FILE), "KAKAO_REFRESH_TOKEN", refresh_token)
    print("✅ KAKAO_REFRESH_TOKEN을 .env에 저장했습니다.")
    print("   이제 main.py를 실행할 수 있습니다!")


if __name__ == "__main__":
    main()
