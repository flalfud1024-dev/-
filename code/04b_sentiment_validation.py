"""
04b_sentiment_validation.py — 감성분석 결과 수동 검증 프레임워크

목적:
  SnowNLP는 전자상거래 리뷰로 학습되어 문학 리뷰 도메인에
  불일치가 발생할 수 있음. 번역본별 층화 무작위 표본 200건을
  연구자가 수동 코딩하여 자동 분석 결과의 타당도를 검증.

산출물:
  1. sentiment_manual_coding_template.csv  (수동 코딩용 템플릿)
  2. 수동 코딩 완료 후 validation_report.csv (신뢰도 지표)

논문 기여:
  방법론 챕터 3.3.4에 "SnowNLP 도메인 적응 검증" 절로 서술.
  → 심사 질문 "SnowNLP가 문학 리뷰에 적합한가?"에 대한 완전 대응.
"""

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score, precision_recall_fscore_support,
    cohen_kappa_score, confusion_matrix
)
from scipy.stats import pearsonr, spearmanr

RANDOM_SEED = 42


def create_coding_template(
    df: pd.DataFrame,
    output_path: str,
    n_per_version: int = 70,
) -> pd.DataFrame:
    """
    번역본별 층화 무작위 표본 추출 → 수동 코딩 템플릿 생성.

    수동 코딩 기준 (연구자 본인 + 제2코더가 독립적으로):
      manual_polarity:  -1(부정) / 0(중립) / 1(긍정)
      manual_intensity:  1(약) / 2(중) / 3(강)
      manual_emotion:   joy/sadness/anger/fear/disgust/surprise/neutral
      notes:            해석의 근거 (텍스트언어학적 관찰)
    """
    rng = np.random.default_rng(RANDOM_SEED)
    samples = []
    for ver in df['version'].unique():
        subset = df[df['version'] == ver]
        n = min(n_per_version, len(subset))
        sample_idx = rng.choice(subset.index, size=n, replace=False)
        samples.append(df.loc[sample_idx])

    template = pd.concat(samples).reset_index(drop=True)

    # 자동 분석 결과는 참고용으로 포함 (단, 코더 편향 방지 위해
    # 실제 수동 코딩 시에는 해당 컬럼을 가린 버전을 배포할 것)
    keep_cols = ['version', 'text', 'rating',
                 'polarity_snownlp', 'polarity_lexicon',
                 'intensity_composite', 'dominant_emotion']
    template = template[[c for c in keep_cols if c in template.columns]]

    # 수동 코딩 빈 컬럼
    template['manual_polarity'] = ''       # -1/0/1
    template['manual_intensity'] = ''      # 1/2/3
    template['manual_emotion'] = ''        # joy/sadness/...
    template['coder_id'] = ''              # coder_A / coder_B
    template['notes'] = ''

    template.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"코딩 템플릿 저장: {output_path}")
    print(f"표본 구성: {len(template)}건 (번역본별 {n_per_version}건)")
    return template


def _discretize_polarity(score: float, neutral_band: float = 0.15) -> int:
    """연속 극성 점수를 -1/0/1 3분법으로 이산화"""
    if pd.isna(score):
        return np.nan
    mid = 0.5 if score <= 1 else 0  # SnowNLP는 [0,1], lexicon은 [-1,1]
    if abs(score - mid) <= neutral_band:
        return 0
    return 1 if score > mid else -1


def compute_validation_metrics(coded_csv: str) -> pd.DataFrame:
    """
    수동 코딩 완료 파일로부터 자동 분석 정확도 산출.

    반환: 번역본별 × 분석기별 검증 지표 테이블
      - Accuracy, Precision, Recall, F1
      - Cohen's Kappa
      - Pearson/Spearman 상관 (연속값)
    """
    df = pd.read_csv(coded_csv)
    df = df[df['manual_polarity'].notna() & (df['manual_polarity'] != '')]
    df['manual_polarity'] = df['manual_polarity'].astype(int)

    results = []
    for ver in df['version'].unique():
        sub = df[df['version'] == ver]
        manual = sub['manual_polarity'].values

        for analyzer, col, band in [
            ('SnowNLP',  'polarity_snownlp', 0.15),
            ('Lexicon',  'polarity_lexicon', 0.10),
        ]:
            pred = sub[col].apply(lambda x: _discretize_polarity(x, band))
            valid = ~(pd.isna(pred) | pd.isna(manual))
            y_true = manual[valid]
            y_pred = pred[valid].astype(int)

            acc = accuracy_score(y_true, y_pred)
            prec, rec, f1, _ = precision_recall_fscore_support(
                y_true, y_pred, average='weighted', zero_division=0
            )
            kappa = cohen_kappa_score(y_true, y_pred)

            # 연속값 상관 (이산화 전 원본)
            try:
                r_pearson, _ = pearsonr(sub[col].dropna(), manual[:len(sub[col].dropna())])
                r_spearman, _ = spearmanr(sub[col].dropna(), manual[:len(sub[col].dropna())])
            except Exception:
                r_pearson = r_spearman = np.nan

            results.append({
                'version': ver,
                'analyzer': analyzer,
                'N': len(y_true),
                'accuracy': round(acc, 3),
                'precision': round(prec, 3),
                'recall': round(rec, 3),
                'F1': round(f1, 3),
                'kappa': round(kappa, 3),
                'pearson_r': round(r_pearson, 3) if not np.isnan(r_pearson) else '-',
                'spearman_r': round(r_spearman, 3) if not np.isnan(r_spearman) else '-',
            })

    return pd.DataFrame(results)


def inter_coder_reliability(coded_csv: str) -> dict:
    """
    두 코더(A, B)가 동일 표본을 코딩한 경우
    Cohen's Kappa로 코더 간 신뢰도 산출.
    논문 3.4.3.3 절에 직접 대응.
    """
    df = pd.read_csv(coded_csv)
    pivot = df.pivot_table(
        index='text', columns='coder_id',
        values='manual_polarity', aggfunc='first'
    ).dropna()

    if {'coder_A', 'coder_B'}.issubset(pivot.columns):
        k_pol = cohen_kappa_score(pivot['coder_A'], pivot['coder_B'])
        return {
            'N_double_coded': len(pivot),
            'kappa_polarity': round(k_pol, 3),
            'interpretation': _kappa_interpretation(k_pol),
        }
    return {'error': '두 코더의 중복 코딩 데이터 부족'}


def _kappa_interpretation(k: float) -> str:
    """Landis & Koch (1977) 기준"""
    if k < 0:         return 'Poor (무의미)'
    if k < 0.20:      return 'Slight'
    if k < 0.40:      return 'Fair'
    if k < 0.60:      return 'Moderate'
    if k < 0.80:      return 'Substantial'
    return 'Almost Perfect (논문 권장 수준)'


if __name__ == '__main__':
    # 1단계: 코딩 템플릿 생성 (분석 완료 후 최초 1회 실행)
    df = pd.read_csv('data/processed/sentiment_full.csv')
    create_coding_template(
        df,
        'data/coding_templates/sentiment_manual_coding_template.csv',
        n_per_version=70,
    )

    # 2단계: 수동 코딩 완료 후 이 블록 실행
    # report = compute_validation_metrics(
    #     'data/coding_templates/sentiment_manual_coding_done.csv'
    # )
    # report.to_csv('output/tables/sentiment_validation.csv', index=False)
    # print(report.to_string(index=False))
