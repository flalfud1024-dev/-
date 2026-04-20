"""
01_preprocessing.py — 豆瓣 리뷰 전처리 파이프라인
jieba 형태소 분석 + 불용어 제거 + 노이즈 필터링
"""

import jieba
import pandas as pd
import re

# ── 사용자 사전: 채식주의자 전용 ──────────────────
CUSTOM_WORDS = [
    '英惠', '仁惠', '韩医生', '姐夫',
    '素食主义者', '韩江', '蒙古斑', '植物'
]
for word in CUSTOM_WORDS:
    jieba.add_word(word)

# ── 불용어: 중국어 일반 + 도서리뷰 특화 ───────────
STOPWORDS = set([
    '的', '了', '是', '在', '我', '都', '也', '就', '很',
    '这', '那', '但', '和', '有', '不', '他', '她', '它',
    '一个', '觉得', '感觉', '非常', '可以', '没有',      # 리뷰 상투어
    '这本书', '作者', '翻译', '出版', '读者'            # 메타담론 (별도 분석)
])


def preprocess_text(text: str) -> list:
    """
    입력: 원시 리뷰 텍스트
    출력: 토큰 리스트
    처리: 한자 추출 → jieba 분절 → 불용어 제거 → 2자 이상 필터
    """
    text = re.sub(r'[^\u4e00-\u9fff]', ' ', text)  # 한자만 유지
    tokens = jieba.cut(text, cut_all=False)         # 정밀 분절
    return [t for t in tokens
            if t not in STOPWORDS and len(t) >= 2]


def load_and_preprocess(filepath: str, version_label: str) -> pd.DataFrame:
    df = pd.read_csv(filepath)

    required_cols = ['text', 'rating', 'date', 'likes']
    assert all(c in df.columns for c in required_cols), \
        f"누락 컬럼 확인 필요: {filepath}"

    df['version'] = version_label
    df['tokens'] = df['text'].apply(preprocess_text)
    df['token_str'] = df['tokens'].apply(' '.join)
    df['token_count'] = df['tokens'].apply(len)

    # 최소 토큰 기준: 10개 (근거는 방법론 챕터에 서술)
    df = df[df['token_count'] >= 10].reset_index(drop=True)

    return df


if __name__ == '__main__':
    dfs = []
    sources = [
        ('data/raw/tianyi_2013.csv',    'tianyi_2013'),
        ('data/raw/taiwan_2016.csv',    'taiwan_2016'),
        ('data/raw/huchutong_2021.csv', 'huchutong_2021'),
    ]
    for path, label in sources:
        df = load_and_preprocess(path, label)
        print(f"[{label}] 유효 리뷰 수: {len(df)}건")
        dfs.append(df)

    all_df = pd.concat(dfs, ignore_index=True)
    all_df.to_csv('data/processed/all_reviews.csv', index=False)
    print("전처리 완료 → data/processed/all_reviews.csv")
