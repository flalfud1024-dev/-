"""
카카오톡 '나에게 보내기' API를 이용한 알림 모듈.

사전 준비:
  1. kakao_auth.py 를 한 번 실행해 KAKAO_REFRESH_TOKEN을 .env에 저장
  2. 카카오 앱 설정 > 카카오 로그인 > 동의항목에서
     '카카오톡 메시지 전송' 권한 활성화 확인
"""

import json
import os
from pathlib import Path

import requests
from dotenv import set_key

from config import KAKAO_REST_API_KEY, KAKAO_REFRESH_TOKEN

_TOKEN_URL = "https://kauth.kakao.com/oauth/token"
_MEMO_URL = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
_ENV_FILE = str(Path(__file__).parent / ".env")
_MAX_TEXT = 200   # 카카오 text 템플릿 최대 글자 수


def _refresh_access_token() -> str:
    resp = requests.post(
        _TOKEN_URL,
        data={
            "grant_type": "refresh_token",
            "client_id": KAKAO_REST_API_KEY,
            "refresh_token": KAKAO_REFRESH_TOKEN,
        },
        timeout=10,
    )
    resp.raise_for_status()
    token_data = resp.json()

    # refresh_token이 갱신됐으면 .env에 저장 (유효기간 1개월 미만일 때 카카오가 재발급)
    new_refresh = token_data.get("refresh_token")
    if new_refresh and new_refresh != KAKAO_REFRESH_TOKEN:
        set_key(_ENV_FILE, "KAKAO_REFRESH_TOKEN", new_refresh)
        os.environ["KAKAO_REFRESH_TOKEN"] = new_refresh

    return token_data["access_token"]


def _send_single(access_token: str, text: str, dart_url: str = "") -> None:
    template: dict = {"object_type": "text", "text": text, "link": {}}
    if dart_url:
        template["link"] = {"web_url": dart_url, "mobile_web_url": dart_url}
        template["button_title"] = "DART 원문 보기"

    resp = requests.post(
        _MEMO_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        data={"template_object": json.dumps(template, ensure_ascii=False)},
        timeout=10,
    )
    resp.raise_for_status()
    result = resp.json()
    if result.get("result_code") != 0:
        raise RuntimeError(f"카카오 메시지 발송 실패: {result}")


def send_message(text: str, dart_url: str = "") -> None:
    """긴 텍스트는 자동으로 분할해 여러 메시지로 전송."""
    access_token = _refresh_access_token()

    chunks: list[str] = []
    current = ""
    for line in text.split("\n"):
        # 현재 chunk에 이 줄을 추가했을 때 한도 초과하면 현재 chunk 저장 후 새로 시작
        addition = ("\n" + line) if current else line
        if len(current) + len(addition) <= _MAX_TEXT:
            current += addition
        else:
            if current:
                chunks.append(current)
            # 단일 줄이 _MAX_TEXT를 넘는 경우 강제 분할
            while len(line) > _MAX_TEXT:
                chunks.append(line[:_MAX_TEXT])
                line = line[_MAX_TEXT:]
            current = line
    if current:
        chunks.append(current)

    for i, chunk in enumerate(chunks):
        # DART 링크는 첫 번째 메시지에만 첨부
        _send_single(access_token, chunk, dart_url if i == 0 else "")
