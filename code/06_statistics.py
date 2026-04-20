"""
06_statistics.py — 통계 검증 종합표 생성
논문 표 3-X로 직접 삽입 가능한 통계 요약표
"""

from itertools import combinations
import pandas as pd
from scipy import stats


def generate_stats_table(df: pd.DataFrame) -> pd.DataFrame:
    """
    논문 방법론 챕터 통계 검증 결과 종합표.
    재현성: 동일 데이터로 동일 수치 반드시 재현됨.
    """
    results = []
    versions = ['tianyi_2013', 'taiwan_2016', 'huchutong_2021']

    for v1, v2 in combinations(versions, 2):
        g1 = df[df['version'] == v1]['sentiment'].dropna()
        g2 = df[df['version'] == v2]['sentiment'].dropna()
        stat, p = stats.mannwhitneyu(g1, g2, alternative='two-sided')
        results.append({
            '비교 그룹': f'{v1} vs {v2}',
            '검정 방법': 'Mann-Whitney U',
            'U 통계량': round(stat, 2),
            'p값': round(p, 4),
            '유의미 여부(α=0.05)': '○' if p < 0.05 else '×',
        })

    return pd.DataFrame(results)


if __name__ == '__main__':
    df = pd.read_csv('data/processed/reviews_with_sentiment.csv')
    table = generate_stats_table(df)
    print(table.to_string(index=False))
    table.to_csv('output/tables/table_stats_summary.csv',
                 index=False, encoding='utf-8-sig')
    print("\n통계표 저장: output/tables/table_stats_summary.csv")
