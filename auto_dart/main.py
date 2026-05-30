from datetime import datetime

from dart_client import fetch_pension_disclosures
from parser import parse_disclosure
from analyzer import analyze
from research_agent import analyze_stock
from storage import load_seen, save_seen
from notifier import send_message

DART_DISCLOSURE_URL = "https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}"


def build_report(results, today: str) -> str:
    lines = [f"📊 국민연금 지분변동 리포트 ({today})", ""]

    categories = [
        ("신규", "🆕"),
        ("매수", "📈"),
        ("매도", "📉"),
        ("유지", "➡️"),
    ]
    for label, emoji in categories:
        items = [r for r in results if r.action == label]
        if not items:
            continue
        lines.append(f"{emoji} {label}")
        for r in items:
            ratio_info = f"{r.curr_ratio:.2f}%"
            if r.prev_ratio is not None:
                diff = r.curr_ratio - r.prev_ratio
                ratio_info += f" ({diff:+.2f}%p)"
            lines.append(f"  • {r.disclosure.corp_name}: {ratio_info}")
        lines.append("")

    return "\n".join(lines).rstrip()


def main() -> None:
    today = datetime.today().strftime("%Y-%m-%d")
    print("🔍 국민연금 공시 수집 시작...")

    raw = fetch_pension_disclosures(days=7)
    print(f"  수집된 공시: {len(raw)}건")

    seen = load_seen()
    new_raw = [item for item in raw if item["rcept_no"] not in seen]
    print(f"  신규 공시: {len(new_raw)}건")

    if not new_raw:
        print("새로운 공시가 없습니다.")
        return

    disclosures = [parse_disclosure(item) for item in new_raw]
    results = analyze(disclosures)

    # 리포트 전송 (DART 링크는 첫 번째 공시 원문)
    first_url = DART_DISCLOSURE_URL.format(rcept_no=new_raw[0]["rcept_no"])
    send_message(build_report(results, today), dart_url=first_url)
    print("  리포트 발송 완료")

    for r in results:
        if r.action in ("매수", "신규"):
            print(f"  {r.disclosure.corp_name} AI 분석 중...")
            dart_url = DART_DISCLOSURE_URL.format(rcept_no=r.disclosure.rcept_no)
            analysis = analyze_stock(r)
            send_message(analysis, dart_url=dart_url)
            print(f"  {r.disclosure.corp_name} 분석 발송 완료")

    save_seen(seen | {item["rcept_no"] for item in new_raw})
    print("✅ 완료")


if __name__ == "__main__":
    main()
