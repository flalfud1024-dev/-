"""
04_sentiment.py — 감성 극성 및 강도 분석 (3-layer)

[Layer 1] 극성(Polarity): SnowNLP + 사전기반 점수 이중 계산
[Layer 2] 강도(Intensity): 강조어 빈도 + 감정어 밀도 + 문장부호 강도
[Layer 3] 감정 범주(Emotion Categories): Ekman 6대 기본감정 기반

재현성:
- 모든 처리는 결정론적(deterministic)
- 번역본별 결과는 data/processed/sentiment_full.csv에 저장
- 논문 4.2.2(감성 극성 및 강도 비교)에 직접 연결
"""

import re
import numpy as np
import pandas as pd
from snownlp import SnowNLP


# ===========================================================
# 사전 정의: 문학 리뷰 도메인 최소 감성사전
# ===========================================================
# 주의: 본 사전은 파일럿용 최소 셋이며, 본 분석에서는
#       大连理工 情感本体库(DUTIR) 또는 BosonNLP 사전으로
#       교체하여 사용해야 함 (논문 방법론 챕터에 근거 명시).
# ===========================================================

# 문학 리뷰 빈출 긍정/부정 어휘 (파일럿용)
POSITIVE_LEXICON = {
    '震撼': 2, '深刻': 2, '精彩': 2, '出色': 2, '杰作': 3,
    '喜欢': 1, '好': 1, '值得': 1, '推荐': 1, '细腻': 2,
    '动人': 2, '优美': 2, '深情': 2, '感人': 2, '共鸣': 2,
}

NEGATIVE_LEXICON = {
    '失望': -2, '糟糕': -2, '无聊': -2, '晦涩': -1, '难懂': -1,
    '讨厌': -2, '差': -1, '烂': -3, '粗糙': -2, '做作': -2,
    '压抑': -1, '不适': -1, '恶心': -2, '残忍': -1, '痛苦': -1,
}

# 강도 강조어 (Degree Adverbs) — 값은 증폭 계수
INTENSIFIERS = {
    '非常': 1.5, '极其': 2.0, '特别': 1.5, '十分': 1.3,
    '很': 1.2, '太': 1.3, '超': 1.5, '真的': 1.2,
    '相当': 1.3, '格外': 1.5, '异常': 1.7, '极': 2.0,
}

# 부정어 (감성 극성 반전)
NEGATORS = {'不', '没', '没有', '未', '非', '别', '无', '并非'}

# Ekman 6대 기본감정 사전 (최소 파일럿)
EKMAN_LEXICON = {
    '기쁨(joy)':     {'高兴', '快乐', '喜悦', '愉快', '欣喜', '感动', '温暖'},
    '슬픔(sadness)': {'悲伤', '难过', '痛苦', '哀伤', '忧郁', '沉重', '压抑'},
    '분노(anger)':   {'愤怒', '生气', '恼火', '愤慨', '气愤', '不满'},
    '공포(fear)':    {'恐惧', '害怕', '恐怖', '惊悚', '不安', '惊吓'},
    '혐오(disgust)': {'厌恶', '恶心', '讨厌', '反感', '嫌弃'},
    '놀람(surprise)':{'惊讶', '震惊', '惊奇', '意外', '震撼', '吃惊'},
}


# ===========================================================
# Layer 1: 극성(Polarity) — 이중 산출
# ===========================================================

def snownlp_polarity(text: str) -> float:
    """SnowNLP 기반 극성 점수 (0=부정, 0.5=중립, 1=긍정)"""
    try:
        return SnowNLP(str(text)).sentiments
    except Exception:
        return np.nan


def lexicon_polarity(tokens: list) -> float:
    """
    사전 기반 극성 점수.
    - 토큰 윈도우(앞 2어)에서 부정어/강조어 스캔
    - 감정어 가중치 합산 → 토큰 수로 정규화 → [-1, 1] 스케일
    """
    if not tokens:
        return np.nan

    score = 0.0
    emotion_count = 0

    for i, token in enumerate(tokens):
        weight = 0
        if token in POSITIVE_LEXICON:
            weight = POSITIVE_LEXICON[token]
        elif token in NEGATIVE_LEXICON:
            weight = NEGATIVE_LEXICON[token]

        if weight == 0:
            continue

        # 직전 2개 토큰에서 부정어/강조어 탐색
        window = tokens[max(0, i - 2):i]
        amplifier = 1.0
        negated = False
        for w in window:
            if w in NEGATORS:
                negated = not negated
            if w in INTENSIFIERS:
                amplifier *= INTENSIFIERS[w]

        adjusted = weight * amplifier * (-1 if negated else 1)
        score += adjusted
        emotion_count += 1

    if emotion_count == 0:
        return 0.0

    # 최대 가능 가중치(약 3*2=6)로 스케일 정규화
    normalized = score / (emotion_count * 6)
    return max(-1.0, min(1.0, normalized))


# ===========================================================
# Layer 2: 강도(Intensity) — 3개 지표
# ===========================================================

def intensifier_ratio(tokens: list) -> float:
    """강조어 비율: 전체 토큰 중 정도부사 출현 비율"""
    if not tokens:
        return 0.0
    return sum(1 for t in tokens if t in INTENSIFIERS) / len(tokens)


def emotion_density(tokens: list) -> float:
    """감정어 밀도: 전체 토큰 중 감성어휘 출현 비율"""
    if not tokens:
        return 0.0
    emotion_words = set(POSITIVE_LEXICON) | set(NEGATIVE_LEXICON)
    return sum(1 for t in tokens if t in emotion_words) / len(tokens)


def punctuation_intensity(text: str) -> float:
    """문장부호 강도: 느낌표/물음표/생략부호의 길이 기반 점수"""
    text = str(text)
    score = 0.0
    # 연속 느낌표: !!!은 !보다 강함
    for match in re.finditer(r'[!！]+', text):
        score += len(match.group()) ** 1.5
    for match in re.finditer(r'[?？]+', text):
        score += len(match.group()) * 0.7
    # 문자 수로 정규화
    return score / max(len(text), 1) * 100


def composite_intensity(tokens: list, text: str) -> float:
    """3개 지표 가중합 (가중치는 파일럿 후 조정 가능)"""
    return (0.4 * intensifier_ratio(tokens)
            + 0.4 * emotion_density(tokens)
            + 0.2 * punctuation_intensity(text))


# ===========================================================
# Layer 3: 감정 범주(Ekman 6-emotion)
# ===========================================================

def emotion_categories(tokens: list) -> dict:
    """각 감정 범주별 출현 빈도 반환"""
    counts = {cat: 0 for cat in EKMAN_LEXICON}
    for t in tokens:
        for cat, lex in EKMAN_LEXICON.items():
            if t in lex:
                counts[cat] += 1
    return counts


# ===========================================================
# 통합 처리
# ===========================================================

def enrich_sentiment(df: pd.DataFrame) -> pd.DataFrame:
    """
    전처리된 DataFrame에 감성 분석 결과 추가.
    필수 컬럼: text, tokens
    """
    # tokens가 문자열이면 리스트로 복원
    if isinstance(df['tokens'].iloc[0], str):
        import ast
        df['tokens'] = df['tokens'].apply(ast.literal_eval)

    # Layer 1: 극성
    df['polarity_snownlp'] = df['text'].apply(snownlp_polarity)
    df['polarity_lexicon'] = df['tokens'].apply(lexicon_polarity)

    # Layer 2: 강도
    df['intensity_intensifier'] = df['tokens'].apply(intensifier_ratio)
    df['intensity_emotion_density'] = df['tokens'].apply(emotion_density)
    df['intensity_punctuation'] = df['text'].apply(punctuation_intensity)
    df['intensity_composite'] = df.apply(
        lambda r: composite_intensity(r['tokens'], r['text']), axis=1
    )

    # Layer 3: 감정 범주 (6개 컬럼 확장)
    emo_df = df['tokens'].apply(emotion_categories).apply(pd.Series)
    emo_df.columns = [f'emo_{c}' for c in emo_df.columns]
    df = pd.concat([df, emo_df], axis=1)

    # 지배적 감정 범주
    emo_cols = [c for c in df.columns if c.startswith('emo_')]
    df['dominant_emotion'] = df[emo_cols].idxmax(axis=1).where(
        df[emo_cols].sum(axis=1) > 0, other='neutral'
    )

    return df


if __name__ == '__main__':
    df = pd.read_csv('data/processed/all_reviews.csv')
    df = enrich_sentiment(df)
    df.to_csv('data/processed/sentiment_full.csv', index=False)
    print(f"감성 분석 완료: {len(df)}건")
    print(f"저장: data/processed/sentiment_full.csv")

    # 번역본별 요약
    summary = df.groupby('version').agg({
        'polarity_snownlp': 'mean',
        'polarity_lexicon': 'mean',
        'intensity_composite': 'mean',
    }).round(4)
    print("\n[번역본별 감성 요약]")
    print(summary)
