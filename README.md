# 한강 『채식주의자』 중문 번역본 비교 연구 방법론

박사학위논문 연구 방법론 아카이브

## 연구 개요

**제목(안):** 번역의 이데올로기적 개입과 독자반응의 변용 — 한강의 『채식주의자』 중문 번역본 비교를 중심으로

**영문 부제:** Ideological Intervention in Translation and the Transformation of Reader Response: A Comparative Study of Chinese Translations of Han Kang's *The Vegetarian*

## 연구 대상 번역본

| 번역자 | 연도 | 지역 | 문자 | 특이점 |
|--------|------|------|------|--------|
| 천일(陳怡) | 2013 | 중국 본토 | 간체 | 외설적 성적 장면 전면 삭제 |
| 천일(陳怡) | 2016 | 타이완 | 번체 | 삭제 장면 복원 번역 |
| 후추통(胡椒筒) | 2021 | 중국 본토 | 간체 | 대안적 프레이밍 |

## 연구 데이터

- 출처: 豆瓣(더우반) 독자 리뷰
- 상태: 수집 완료

## 폴더 구조

```
.
├── README.md                      # 본 문서
├── docs/
│   ├── 01_research_design.md      # 연구 설계 및 이론 프레임
│   ├── 02_thesis_outline.md       # 논문 목차 (한외대 내규 반영)
│   ├── 03_methodology_notes.md    # 방법론 상세 노트
│   ├── 04_ai_disclosure.md        # AI 활용 공시 및 각주 샘플
│   ├── 05_sentiment_methodology.md # 감성분석 방법론 정당화
│   └── 06_prd_crawler.md          # 豆瓣 크롤러 PRD (제품요구사항정의서)
└── code/
    ├── requirements.txt           # 패키지 버전 고정
    ├── 00_setup.py                # 환경 설정
    ├── 01_preprocessing.py        # 전처리
    ├── 02_tfidf.py                # TF-IDF 분석
    ├── 03_lda.py                  # LDA 토픽모델링
    ├── 04_sentiment.py            # 감성분석 (극성+강도+감정범주 3-layer)
    ├── 04b_sentiment_validation.py # 수동 코딩 검증 프레임워크
    ├── 04c_sentiment_stats.py     # 감성 통계검정 (결정트리+효과크기)
    ├── 05_network.py              # 인물 공출현 네트워크
    └── 06_statistics.py           # 통계 검증
```
