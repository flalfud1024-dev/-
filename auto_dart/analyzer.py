from dataclasses import dataclass
from typing import Literal

from parser import Disclosure
from storage import load_history, save_history

Action = Literal["매수", "매도", "유지", "신규"]


@dataclass
class AnalysisResult:
    disclosure: Disclosure
    action: Action
    prev_ratio: float | None
    curr_ratio: float


def analyze(disclosures: list[Disclosure]) -> list[AnalysisResult]:
    history = load_history()
    results: list[AnalysisResult] = []

    for d in disclosures:
        prev = history.get(d.corp_code)
        curr = d.hold_ratio

        if prev is None:
            action: Action = "신규"
        elif curr > prev + 0.01:   # 0.01%p 이상 증가를 매수로 판정
            action = "매수"
        elif curr < prev - 0.01:
            action = "매도"
        else:
            action = "유지"

        results.append(AnalysisResult(
            disclosure=d,
            action=action,
            prev_ratio=prev,
            curr_ratio=curr,
        ))
        history[d.corp_code] = curr

    save_history(history)
    return results
