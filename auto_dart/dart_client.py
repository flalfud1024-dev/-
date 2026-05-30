import requests
from datetime import datetime, timedelta
from config import DART_API_KEY

BASE_URL = "https://opendart.fss.or.kr/api"


def fetch_pension_disclosures(days: int = 7) -> list[dict]:
    end_dt = datetime.today()
    start_dt = end_dt - timedelta(days=days)

    params = {
        "crtfc_key": DART_API_KEY,
        "bgn_de": start_dt.strftime("%Y%m%d"),
        "end_de": end_dt.strftime("%Y%m%d"),
        "page_count": 100,
    }

    resp = requests.get(f"{BASE_URL}/majorstock.json", params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    if data.get("status") not in ("000",):
        if data.get("status") == "013":  # 조회 결과 없음
            return []
        raise RuntimeError(f"DART API 오류: {data.get('status')} {data.get('message')}")

    items = data.get("list", [])
    return [item for item in items if "국민연금" in item.get("flr_nm", "")]
