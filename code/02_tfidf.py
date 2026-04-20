"""
02_tfidf.py — TF-IDF 기반 번역본별 특징어 추출
상위 N개 특징어 → 논문 그림 삽입용 시각화
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.feature_extraction.text import TfidfVectorizer

# 논문용 폰트 설정 (한중 혼용)
plt.rcParams['font.family'] = 'Noto Sans CJK SC'
plt.rcParams['figure.dpi'] = 300


def extract_top_tfidf(corpus: list, n_top: int = 30) -> pd.DataFrame:
    """번역본별 특징어 상위 N개 추출"""
    vec = TfidfVectorizer(max_features=500)
    matrix = vec.fit_transform(corpus)
    scores = np.array(matrix.mean(axis=0)).flatten()
    vocab = vec.get_feature_names_out()
    return (pd.DataFrame({'word': vocab, 'tfidf': scores})
            .sort_values('tfidf', ascending=False).head(n_top))


def plot_comparison(df: pd.DataFrame, output_path: str):
    fig, axes = plt.subplots(1, 3, figsize=(18, 8))
    versions = ['tianyi_2013', 'taiwan_2016', 'huchutong_2021']
    labels = ['천일본(2013)', '천일본(2016)', '후추통본(2021)']

    for ax, ver, label in zip(axes, versions, labels):
        subset = df[df['version'] == ver]
        top = extract_top_tfidf(subset['token_str'].tolist(), n_top=20)
        ax.barh(top['word'], top['tfidf'], color='steelblue')
        ax.invert_yaxis()
        ax.set_title(label, fontsize=14, fontweight='bold')
        ax.set_xlabel('TF-IDF 점수')

    plt.suptitle('번역본별 특징어 비교 (상위 20개)',
                 fontsize=16, fontweight='bold')
    plt.tight_layout()
    plt.savefig(output_path, bbox_inches='tight')
    print(f"저장: {output_path}")


if __name__ == '__main__':
    df = pd.read_csv('data/processed/all_reviews.csv')
    plot_comparison(df, 'output/figures/fig1_tfidf_comparison.png')
