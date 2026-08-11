# -*- coding: utf-8 -*-
"""자극 파일 읽기와 후보 세트 조립.

CSV가 주는 것은 제품군 목록과 제품군마다의 특징 풀뿐이다. 브랜드명, 브랜드와
특징의 짝, 화면에 놓이는 순서, 가격은 전부 참가자마다 그 자리에서 뽑는다.
고정된 짝이 없어야 특정 이름이나 특정 문구가 선호를 밀지 않는다.

psychopy를 import하지 않는다. 자극 구성만 따로 검사할 수 있게 하려는 것.
"""

from __future__ import annotations

import csv
import io
import os
import random
import re
import string
from dataclasses import dataclass, field
from typing import Dict, List, Sequence

from . import config as C


# ─────────────────────────────────────────────
#  조사 붙이기
# ─────────────────────────────────────────────

_JOSA_PAIRS = {
    "이/가": ("이", "가"),
    "은/는": ("은", "는"),
    "을/를": ("을", "를"),
    "과/와": ("과", "와"),
}

# 알파벳으로 끝나는 말은 읽는 소리를 기준으로 받침 유무를 판정한다.
# 예: ChatGPT는 "티"로 읽으니 받침이 없다 -> "ChatGPT가".
_LATIN_FINAL_HAS_BATCHIM = {
    "l": True, "m": True, "n": True, "r": True, "g": True,
    # 나머지 자음/모음은 받침 없음으로 본다
}


def _has_batchim(word: str) -> bool:
    """마지막 글자에 받침이 있는지."""
    word = re.sub(r"[\]\)\}\s\.\,]+$", "", word.strip())
    if not word:
        return False
    ch = word[-1]
    if "가" <= ch <= "힣":
        return (ord(ch) - 0xAC00) % 28 != 0
    if ch.isdigit():
        return ch in "0136780"          # 영, 일, 삼, 육, 칠, 팔, 십
    low = ch.lower()
    if "a" <= low <= "z":
        return _LATIN_FINAL_HAS_BATCHIM.get(low, False)
    return False


def apply_josa(text: str, word: str) -> str:
    """'{src}{이/가}' 꼴의 자리표시자를 실제 조사로 바꾼다."""
    filled = text.replace("{src}", word)
    batchim = _has_batchim(word)
    for token, (with_b, without_b) in _JOSA_PAIRS.items():
        filled = filled.replace("{" + token + "}", with_b if batchim else without_b)
    return filled


# ─────────────────────────────────────────────
#  자료 구조
# ─────────────────────────────────────────────


@dataclass
class Source:
    source_code: str
    label: str          # 과제 화면에 나오는 문구. 예: [ChatGPT]
    short_name: str     # 설문 문장 안에서 부르는 이름. 예: ChatGPT
    intro_text: str


@dataclass
class Detail:
    category_code: str
    detail_type: str    # 'UT' 또는 'HE'
    text: str


@dataclass
class Category:
    category_code: str
    category_kr: str
    major_class: str
    price_low: int
    price_high: int


@dataclass
class Candidate:
    """화면에 나오는 후보 하나. 이름과 특징은 그 자리에서 짝지어진 것이다."""
    brand: str
    detail: Detail

    @property
    def line(self) -> str:
        return "%s  -  %s" % (self.brand, self.detail.text)


@dataclass
class CandidateSet:
    """후보 3개 묶음. 과제의 최소 단위."""
    category_code: str
    category_kr: str
    set_id: int
    candidates: List[Candidate]
    price: int
    set_key: str = field(init=False)

    def __post_init__(self) -> None:
        self.set_key = "%s_s%d" % (self.category_code, self.set_id)


@dataclass
class SurveyItem:
    block: str
    item_id: str
    dimension: str
    text: str
    left_anchor: str
    right_anchor: str

    def rendered(self, source_name: str) -> str:
        return apply_josa(self.text, source_name)


# ─────────────────────────────────────────────
#  읽기
# ─────────────────────────────────────────────


def _read_csv(path: str) -> List[Dict[str, str]]:
    if not os.path.exists(path):
        raise FileNotFoundError("자극 파일을 찾을 수 없습니다: %s" % path)
    with io.open(path, encoding="utf-8-sig", newline="") as fh:
        rows = [r for r in csv.DictReader(fh) if any((v or "").strip() for v in r.values())]
    if not rows:
        raise ValueError("자극 파일이 비어 있습니다: %s" % path)
    return rows


def load_sources(stim_dir: str = None) -> List[Source]:
    rows = _read_csv(os.path.join(stim_dir or C.STIM_DIR, "sources.csv"))
    sources = [Source(**{k: (v or "").strip() for k, v in r.items()}) for r in rows]
    if len(sources) < 2:
        raise ValueError("정보원이 2개 이상이어야 합니다.")
    return sources


def load_categories(stim_dir: str = None) -> Dict[str, Category]:
    rows = _read_csv(os.path.join(stim_dir or C.STIM_DIR, "categories.csv"))
    cats = {}
    for r in rows:
        code = r["category_code"].strip()
        low, high = int(r["price_low"]), int(r["price_high"])
        if low > high:
            raise ValueError("%s: price_low가 price_high보다 큽니다." % code)
        cats[code] = Category(
            category_code=code,
            category_kr=r["category_kr"].strip(),
            major_class=r["major_class"].strip(),
            price_low=low,
            price_high=high,
        )
    return cats


def load_details(stim_dir: str = None) -> Dict[str, List[Detail]]:
    """제품군마다의 특징 풀. 한 세트가 여기서 골라 쓴다."""
    rows = _read_csv(os.path.join(stim_dir or C.STIM_DIR, "details.csv"))
    pools: Dict[str, List[Detail]] = {}
    for r in rows:
        d = Detail(
            category_code=r["category_code"].strip(),
            detail_type=r["detail_type"].strip().upper(),
            text=r["text"].strip(),
        )
        if d.detail_type not in ("UT", "HE"):
            raise ValueError("detail_type은 UT 또는 HE여야 합니다: %s" % d.detail_type)
        pools.setdefault(d.category_code, []).append(d)

    need = C.CANDIDATES_PER_SET + C.N_EXTRA_DETAIL_LINES
    for code, pool in pools.items():
        if len(pool) < need:
            raise ValueError(
                "%s의 특징이 %d개뿐입니다. 후보 %d개와 결정 국면 추가 %d줄을 채우려면 "
                "최소 %d개가 있어야 합니다."
                % (code, len(pool), C.CANDIDATES_PER_SET, C.N_EXTRA_DETAIL_LINES, need)
            )
    return pools


def load_survey_items(stim_dir: str = None) -> Dict[str, List[SurveyItem]]:
    rows = _read_csv(os.path.join(stim_dir or C.STIM_DIR, "questions.csv"))
    blocks: Dict[str, List[SurveyItem]] = {}
    for r in rows:
        item = SurveyItem(**{k: (v or "").strip() for k, v in r.items()})
        blocks.setdefault(item.block, []).append(item)
    return blocks


# ─────────────────────────────────────────────
#  브랜드명
# ─────────────────────────────────────────────

_BRAND_BLOCKLIST = {
    "ass", "fuck", "shit", "cock", "dick", "cunt", "nigg", "rape",
    "kkk", "sex", "piss", "damn", "hell", "nazi",
}


def make_brand_name(rng: random.Random, used: set) -> str:
    """알파벳 4~5자, 대소문자 섞인 이름 하나.

    발음 가능한 조어를 쓰면 음상이 선호를 밀 수 있어서 무작위 문자열을 쓴다.
    """
    used_lower = {u.lower() for u in used}
    while True:
        n = rng.choice(C.BRAND_LEN_CHOICES)
        s = "".join(rng.choice(string.ascii_letters) for _ in range(n))
        low = s.lower()
        if low in used_lower:
            continue                                # 대소문자만 다른 이름 금지
        if any(bad in low for bad in _BRAND_BLOCKLIST):
            continue
        if re.search(r"(.)\1\1", low):
            continue                                # 같은 글자 3연속 금지
        if len(set(low)) < 3:
            continue                                # 글자 종류가 너무 적으면 버린다
        used.add(s)
        return s


# ─────────────────────────────────────────────
#  후보 세트 조립
# ─────────────────────────────────────────────


def build_candidate_sets(
    categories: Dict[str, Category],
    detail_pools: Dict[str, List[Detail]],
    rng: random.Random,
    sets_per_category: int = None,
) -> List[CandidateSet]:
    """제품군마다 후보 세트를 만든다.

    한 세트 안에서 지키는 것은 두 가지다. 브랜드명이 서로 다를 것, 특징이 서로
    다를 것. 어느 이름에 어느 특징이 붙는지는 매번 새로 뽑는다.

    가격은 세트 단위로 하나만 정한다. 세 후보가 같은 가격을 쓰기 때문에 어느
    후보가 추천되든 결정 국면의 가격이 같고, 추천과 가격이 엉키지 않는다.
    """
    n_sets = C.SETS_PER_CATEGORY if sets_per_category is None else sets_per_category
    n_cand = C.CANDIDATES_PER_SET
    used_brands: set = set()
    sets: List[CandidateSet] = []

    for code in sorted(categories):
        cat = categories[code]
        pool = detail_pools.get(code)
        if not pool:
            raise ValueError("details.csv에 %s의 특징이 없습니다." % code)

        for set_id in range(1, n_sets + 1):
            details = rng.sample(pool, n_cand)          # 세트 안에서 특징 안 겹치게
            brands = [make_brand_name(rng, used_brands) for _ in range(n_cand)]
            rng.shuffle(brands)                         # 이름과 특징의 짝을 한 번 더 섞는다
            candidates = [Candidate(b, d) for b, d in zip(brands, details)]
            rng.shuffle(candidates)                     # 화면에 놓이는 순서도 섞는다

            price = rng.randrange(cat.price_low, cat.price_high + 1, C.PRICE_STEP)
            sets.append(
                CandidateSet(
                    category_code=code,
                    category_kr=cat.category_kr,
                    set_id=set_id,
                    candidates=candidates,
                    price=price,
                )
            )
    return sets


def extra_detail_lines(
    cs: CandidateSet,
    detail_pools: Dict[str, List[Detail]],
    rng: random.Random,
) -> List[str]:
    """결정 국면에서 추천 제품 밑에 덧붙일 줄.

    추천된 후보가 정보 국면에서 달고 있던 특징은 task 쪽이 맨 위에 놓는다.
    여기서는 그 아래 줄만 돌려준다. 세트에 이미 쓰인 특징은 빼고 남은 풀에서
    뽑아, 화면에 같은 문구가 두 번 나오지 않게 한다.
    """
    used = {c.detail.text for c in cs.candidates}
    rest = [d for d in detail_pools[cs.category_code] if d.text not in used]
    rng.shuffle(rest)
    return [d.text for d in rest[: C.N_EXTRA_DETAIL_LINES]]


def format_price(won: int) -> str:
    return "{:,}원".format(won)


def source_pairs(sources: Sequence[Source]) -> List[tuple]:
    """유사도 쌍. 정보원 6개면 15쌍."""
    return [
        (sources[i], sources[j])
        for i in range(len(sources))
        for j in range(i + 1, len(sources))
    ]
