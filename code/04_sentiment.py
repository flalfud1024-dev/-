"""
04_sentiment.py — 감성분석 (SnowNLP)
전체 감성 분포 + 인물별 감성 + 통계 검증
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from snownlp import SnowNLP


def get_sentiment(text) -> float:
    try:
        return SnowNLP(str(text)).sentiments  # 0(부정)~1(긍정)
    except Exception:
        return None


def analyze_by_character(df: pd.DataFrame) -> pd.DataFrame:
    """
    인물별 감성 분석 — 단순 전체 감성을 넘어
    영혜/남편/형부/인혜 언급 리뷰만 추출하여 각각 분석
    """
    char_map = {
        '영혜':  ['英惠', '她'],
        '남편':  ['韩医生', '丈夫', '他的丈夫'],
        '형부':  ['姐夫', '哥哥'],
        '인혜':  ['仁惠', '姐姐'],
    }
    results = []
    for char_kr, char_zh_list in char_map.items():
        pattern = '|'.join(char_zh_list)
        mask = df['text'].str.contains(pattern, na=False)
        sub = df[mask].copy()
        sub['character'] = char_kr
        results.append(sub)
    return pd.concat(results, ignore_index=True)


def plot_sentiment_distribution(df: pd.DataFrame, output_path: str):
    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    versions = ['tianyi_2013', 'taiwan_2016', 'huchutong_2021']
    version_labels = ['천일본(2013)', '천일본(2016)', '후추통본(2021)']

    # 상단: 전체 감성 분포
    for ax, ver, label in zip(axes[0], versions, version_labels):
        data = df[df['version'] == ver]['sentiment'].dropna()
        sns.histplot(data, bins=20, ax=ax, kde=True, color='steelblue')
        ax.axvline(data.mean(), color='red', linestyle='--',
                   label=f'평균: {data.mean():.3f}')
        ax.set_title(f'{label}\n전체 감성 분포', fontsize=12)
        ax.legend()

    # 하단: 인물별 감성 박스플롯
    char_df = analyze_by_character(df)
    for ax, ver, label in zip(axes[1], versions, version_labels):
        subset = char_df[char_df['version'] == ver]
        sns.boxplot(data=subset, x='character', y='sentiment', ax=ax)
        ax.set_title(f'{label}\n인물별 감성', fontsize=12)
        ax.set_ylim(0, 1)

    plt.tight_layout()
    plt.savefig(output_path, bbox_inches='tight', dpi=300)


if __name__ == '__main__':
    df = pd.read_csv('data/processed/all_reviews.csv')
    df['sentiment'] = df['text'].apply(get_sentiment)
    df.to_csv('data/processed/reviews_with_sentiment.csv', index=False)
    plot_sentiment_distribution(df, 'output/figures/fig2_sentiment.png')

    # Mann-Whitney U 검정
    g1 = df[df['version'] == 'tianyi_2013']['sentiment'].dropna()
    g2 = df[df['version'] == 'huchutong_2021']['sentiment'].dropna()
    stat, p = stats.mannwhitneyu(g1, g2, alternative='two-sided')
    print(f"\n[통계검증] 천일2013 vs 후추통2021")
    print(f"  Mann-Whitney U = {stat:.2f}, p = {p:.4f}")
    print(f"  → {'유의미한 차이 있음' if p < 0.05 else '유의미한 차이 없음'} (α=0.05)")
