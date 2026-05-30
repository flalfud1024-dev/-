from dataclasses import dataclass


@dataclass
class Disclosure:
    rcept_no: str
    rcept_dt: str
    corp_code: str
    corp_name: str
    hold_ratio: float   # 보유 비율 (%)
    flr_nm: str


def parse_disclosure(item: dict) -> Disclosure:
    # DART API 버전에 따라 필드명이 다를 수 있어 순서대로 시도
    ratio_candidates = [
        "stkqy_rate", "hold_ratio", "hold_qota_rt", "stkqy_irds_rate",
        "trmend_hd_stkqy_rt", "change_hd_stkqy_rate",
    ]
    hold_ratio = 0.0
    for field in ratio_candidates:
        raw = item.get(field)
        if raw is not None and raw != "":
            try:
                hold_ratio = float(str(raw).replace("%", "").replace(",", ""))
                break
            except (ValueError, TypeError):
                continue

    return Disclosure(
        rcept_no=item.get("rcept_no", ""),
        rcept_dt=item.get("rcept_dt", ""),
        corp_code=item.get("corp_code", ""),
        corp_name=item.get("corp_name", ""),
        hold_ratio=hold_ratio,
        flr_nm=item.get("flr_nm", ""),
    )
