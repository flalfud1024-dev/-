# 00_setup.py — 논문 재현성 선언 블록
# =============================================
# 논문: 번역의 이데올로기적 개입과 독자반응의 변용
# 분석 환경: Python 3.10.x
# 최종 실행일: YYYY-MM-DD
# =============================================

import random
import numpy as np

# 전역 랜덤 시드 고정 (재현성 보장 핵심)
RANDOM_SEED = 42
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)

# 번역본 레이블 전역 정의
VERSIONS = {
    'tianyi_2013': '천일본(2013, 간체)',
    'taiwan_2016': '천일본(2016, 번체)',
    'huchutong_2021': '후추통본(2021, 간체)'
}
