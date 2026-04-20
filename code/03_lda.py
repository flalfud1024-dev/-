"""
03_lda.py — LDA 토픽모델링
코히런스 스코어(c_v)로 최적 토픽 수 결정 → 재현성 보장
"""

import ast
import pandas as pd
from gensim import corpora, models
from gensim.models.coherencemodel import CoherenceModel
import pyLDAvis
import pyLDAvis.gensim_models as gensimvis

RANDOM_SEED = 42


def find_optimal_topics(corpus, dictionary, token_lists,
                        min_k: int = 3, max_k: int = 8) -> int:
    """
    코히런스 스코어(c_v)로 최적 토픽 수 결정.
    논문 방법론 챕터에 이 과정을 반드시 서술.
    """
    scores = {}
    for k in range(min_k, max_k + 1):
        model = models.LdaModel(
            corpus, num_topics=k, id2word=dictionary,
            passes=30, random_state=RANDOM_SEED
        )
        cm = CoherenceModel(
            model=model, texts=token_lists,
            dictionary=dictionary, coherence='c_v'
        )
        scores[k] = cm.get_coherence()
        print(f"  k={k}: coherence={scores[k]:.4f}")
    optimal = max(scores, key=scores.get)
    print(f"→ 최적 토픽 수: {optimal}")
    return optimal


def run_lda_for_version(df: pd.DataFrame, version_label: str):
    subset = df[df['version'] == version_label]

    token_lists = [ast.literal_eval(t) if isinstance(t, str) else t
                   for t in subset['tokens']]

    dictionary = corpora.Dictionary(token_lists)
    dictionary.filter_extremes(no_below=3, no_above=0.85)
    corpus = [dictionary.doc2bow(doc) for doc in token_lists]

    print(f"\n[{version_label}] 최적 토픽 수 탐색 중...")
    optimal_k = find_optimal_topics(corpus, dictionary, token_lists)

    lda = models.LdaModel(
        corpus, num_topics=optimal_k, id2word=dictionary,
        passes=30, random_state=RANDOM_SEED
    )

    print(f"\n[{version_label}] 토픽 구성:")
    for idx, topic in lda.print_topics(num_words=10):
        print(f"  Topic {idx}: {topic}")

    vis = gensimvis.prepare(lda, corpus, dictionary)
    pyLDAvis.save_html(vis, f'output/figures/lda_{version_label}.html')
    print(f"LDA 시각화 저장: lda_{version_label}.html")

    return lda


if __name__ == '__main__':
    df = pd.read_csv('data/processed/all_reviews.csv')
    for ver in ['tianyi_2013', 'taiwan_2016', 'huchutong_2021']:
        run_lda_for_version(df, ver)
