"""
04c_sentiment_stats.py — 감성 극성·강도의 통계 검증

통계 결정 트리:
  1. Shapiro-Wilk 정규성 검정
  2a. 정규 분포 → Welch's t-test (2군) / ANOVA (3군)
  2b. 비정규 → Mann-Whitney U (2군) / Kruskal-Wallis (3군)
  3. 3군 비교 시 유의하면 → Dunn's post-hoc (Bonferroni 보정)
  4. 효과크기(effect size) 산출: Cohen's d 또는 rank-biserial r
  5. 부트스트랩 95% 신뢰구간 (N=10,000)

논문 대응:
  - 방법론 3.3.6 "통계 검증 방법"에 결정 트리 도식화
  - 4.2.2 / 5.2.3 / 6.2.3 각 결과 챕터에 검증표 삽입
"""

from itertools import combinations
import numpy as np
import pandas as pd
from scipy import stats

RANDOM_SEED = 42


# ===========================================================
# 정규성 및 검정 방법 선택
# ===========================================================

def test_normality(values: np.ndarray) -> dict:
    """Shapiro-Wilk. N>5000이면 subsample."""
    values = values[~np.isnan(values)]
    if len(values) < 3:
        return {'W': np.nan, 'p': np.nan, 'normal': False}
    if len(values) > 5000:
        rng = np.random.default_rng(RANDOM_SEED)
        values = rng.choice(values, size=5000, replace=False)
    W, p = stats.shapiro(values)
    return {'W': round(W, 4), 'p': round(p, 4), 'normal': p > 0.05}


# ===========================================================
# 효과크기
# ===========================================================

def cohens_d(a, b) -> float:
    """모수 검정용 효과크기"""
    a, b = np.array(a), np.array(b)
    pooled = np.sqrt(((len(a) - 1) * a.var(ddof=1)
                      + (len(b) - 1) * b.var(ddof=1))
                     / (len(a) + len(b) - 2))
    return (a.mean() - b.mean()) / pooled if pooled > 0 else 0.0


def rank_biserial(u: float, n1: int, n2: int) -> float:
    """Mann-Whitney U에 대응하는 효과크기"""
    return 1 - (2 * u) / (n1 * n2)


def _d_interpretation(d: float) -> str:
    """Cohen(1988): |d|<0.2 trivial, 0.2~0.5 small, 0.5~0.8 medium, >0.8 large"""
    ad = abs(d)
    if ad < 0.2:  return 'trivial'
    if ad < 0.5:  return 'small'
    if ad < 0.8:  return 'medium'
    return 'large'


# ===========================================================
# 부트스트랩 신뢰구간
# ===========================================================

def bootstrap_mean_diff_ci(
    a: np.ndarray, b: np.ndarray,
    n_boot: int = 10000, ci: float = 0.95,
) -> tuple:
    """두 집단 평균차의 부트스트랩 신뢰구간"""
    a = a[~np.isnan(a)]
    b = b[~np.isnan(b)]
    rng = np.random.default_rng(RANDOM_SEED)
    diffs = np.empty(n_boot)
    for i in range(n_boot):
        sa = rng.choice(a, size=len(a), replace=True)
        sb = rng.choice(b, size=len(b), replace=True)
        diffs[i] = sa.mean() - sb.mean()
    lo = np.percentile(diffs, (1 - ci) / 2 * 100)
    hi = np.percentile(diffs, (1 + ci) / 2 * 100)
    return round(lo, 4), round(hi, 4)


# ===========================================================
# 2군 비교
# ===========================================================

def compare_two_groups(a, b, name_a: str, name_b: str, metric: str) -> dict:
    a = np.array(a)[~np.isnan(a)]
    b = np.array(b)[~np.isnan(b)]
    norm_a = test_normality(a)
    norm_b = test_normality(b)
    both_normal = norm_a['normal'] and norm_b['normal']

    if both_normal:
        test_name = "Welch's t-test"
        stat, p = stats.ttest_ind(a, b, equal_var=False)
        effect = cohens_d(a, b)
        effect_label = "Cohen's d"
    else:
        test_name = 'Mann-Whitney U'
        stat, p = stats.mannwhitneyu(a, b, alternative='two-sided')
        effect = rank_biserial(stat, len(a), len(b))
        effect_label = 'rank-biserial r'

    ci_lo, ci_hi = bootstrap_mean_diff_ci(a, b)

    return {
        'metric': metric,
        'group_A': name_a,
        'group_B': name_b,
        'N_A': len(a),
        'N_B': len(b),
        'mean_A': round(a.mean(), 4),
        'mean_B': round(b.mean(), 4),
        'normality_A(p)': norm_a['p'],
        'normality_B(p)': norm_b['p'],
        'test': test_name,
        'statistic': round(stat, 3),
        'p_value': round(p, 4),
        'significant(α=.05)': '○' if p < 0.05 else '×',
        'effect_size_label': effect_label,
        'effect_size': round(effect, 3),
        'effect_magnitude': _d_interpretation(effect),
        'bootstrap_95CI': f'[{ci_lo}, {ci_hi}]',
    }


# ===========================================================
# 3군 비교 + post-hoc
# ===========================================================

def compare_three_groups(df: pd.DataFrame, metric: str) -> dict:
    groups = [df[df['version'] == v][metric].dropna().values
              for v in df['version'].unique()]
    labels = list(df['version'].unique())
    all_normal = all(test_normality(g)['normal'] for g in groups)

    if all_normal:
        test_name = 'One-way ANOVA'
        stat, p = stats.f_oneway(*groups)
    else:
        test_name = 'Kruskal-Wallis H'
        stat, p = stats.kruskal(*groups)

    # Post-hoc: 유의하면 pairwise 실시 + Bonferroni 보정
    post_hoc = []
    if p < 0.05:
        n_pairs = len(list(combinations(labels, 2)))
        for la, lb in combinations(labels, 2):
            a = df[df['version'] == la][metric].dropna().values
            b = df[df['version'] == lb][metric].dropna().values
            u, p_pair = stats.mannwhitneyu(a, b, alternative='two-sided')
            p_adj = min(p_pair * n_pairs, 1.0)  # Bonferroni
            post_hoc.append({
                'pair': f'{la} vs {lb}',
                'U': round(u, 2),
                'p_raw': round(p_pair, 4),
                'p_bonferroni': round(p_adj, 4),
                'significant': '○' if p_adj < 0.05 else '×',
            })

    return {
        'metric': metric,
        'test': test_name,
        'statistic': round(stat, 3),
        'p_value': round(p, 4),
        'significant(α=.05)': '○' if p < 0.05 else '×',
        'post_hoc': post_hoc,
    }


# ===========================================================
# 전체 실행 및 논문용 표 생성
# ===========================================================

def run_full_sentiment_stats(df: pd.DataFrame) -> dict:
    """논문 4.2.2 / 5.2.3 / 6.2.3 통계표 전부 산출"""
    metrics = [
        'polarity_snownlp',
        'polarity_lexicon',
        'intensity_composite',
        'intensity_emotion_density',
    ]

    # 3군 비교
    three_way = [compare_three_groups(df, m) for m in metrics]

    # 2군 pairwise (연구별 핵심 비교)
    research_pairs = {
        '연구1': ('tianyi_2013',   'taiwan_2016'),
        '연구2': ('tianyi_2013',   'huchutong_2021'),
        '연구3': ('huchutong_2021', 'taiwan_2016'),
    }
    pairwise = []
    for label, (v1, v2) in research_pairs.items():
        for m in metrics:
            row = compare_two_groups(
                df[df['version'] == v1][m].values,
                df[df['version'] == v2][m].values,
                v1, v2, m,
            )
            row['research'] = label
            pairwise.append(row)

    return {'three_way': three_way, 'pairwise': pd.DataFrame(pairwise)}


if __name__ == '__main__':
    df = pd.read_csv('data/processed/sentiment_full.csv')
    report = run_full_sentiment_stats(df)

    # 3군 비교 출력
    print("\n[3군 비교: Kruskal-Wallis/ANOVA]")
    for r in report['three_way']:
        print(f"  {r['metric']}: {r['test']} = {r['statistic']}, "
              f"p = {r['p_value']} [{r['significant(α=.05)']}]")
        for ph in r.get('post_hoc', []):
            print(f"    └ {ph['pair']}: p_adj = {ph['p_bonferroni']} "
                  f"[{ph['significant']}]")

    # Pairwise 표 저장
    report['pairwise'].to_csv(
        'output/tables/table_sentiment_stats.csv',
        index=False, encoding='utf-8-sig'
    )
    print("\n저장: output/tables/table_sentiment_stats.csv")
