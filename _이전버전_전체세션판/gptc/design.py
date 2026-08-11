# -*- coding: utf-8 -*-
"""시행 설계와 무작위화.

지켜야 하는 조건

  1. 관심도가 가장 낮은 제품군 몇 개를 뺀다
  2. 남은 제품군마다 후보 세트를 만들고, 세트마다 정해진 횟수만큼 등장시킨다
  3. 같은 세트가 다시 나올 때 화면은 글자 그대로 같다. 정보원 라벨만 바뀐다
  4. 정보원마다 같은 수의 시행을 맡는다
  5. 추천 제품이 화면 몇 번째 줄에 있었는지가 정보원마다 고르게 나뉜다
  6. 같은 정보원, 같은 제품군이 연속으로 몰리지 않는다
  7. 같은 세트의 다음 등장은 충분히 뒤에 온다

5번은 원래 "추천이 참가자 기준 몇 순위인가"를 고르게 맞추던 자리였다. 1단계에서
순위를 받지 않기로 하면서 그 값이 없어졌고, 대신 화면 위치를 맞춘다. 특정
정보원이 늘 맨 윗줄만 추천하는 쏠림을 막는다.

시행 수는 config의 숫자에서 나온다. psychopy를 import하지 않는다.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Sequence

from . import config as C
from .stimuli import CandidateSet, Detail, Source


MIN_REPEAT_LAG = 6          # 같은 세트가 다시 나오기까지 최소 시행 간격


class DesignError(RuntimeError):
    """제약을 만족하는 배치를 못 찾았을 때."""


@dataclass
class Trial:
    trial_number: int
    block: str                  # 'practice' 또는 'main'
    set_key: str
    category_code: str
    category_kr: str
    set_id: int
    source_code: str
    source_label: str
    repetition: int             # 이 세트의 몇 번째 등장인지
    price: int
    rec_position: int           # 추천 제품이 놓인 줄 (1부터)
    rec_brand: str
    rec_detail: str             # 추천 제품이 정보 국면에서 달고 있던 특징
    rec_detail_type: str        # 그 특징이 UT인지 HE인지
    candidate_brands: List[str]     # 화면에 놓인 순서대로
    candidate_details: List[str]
    extra_lines: List[str]      # 결정 국면에서 특징 아래 붙는 줄

    def to_row(self) -> dict:
        row = asdict(self)
        for key in ("candidate_brands", "candidate_details", "extra_lines"):
            row[key] = " | ".join(getattr(self, key))
        return row


# ─────────────────────────────────────────────
#  런 제약 검사
# ─────────────────────────────────────────────


def _max_run_ok(seq: Sequence, max_run: int) -> bool:
    run = 1
    for i in range(1, len(seq)):
        if seq[i] == seq[i - 1]:
            run += 1
            if run > max_run:
                return False
        else:
            run = 1
    return True


def _repeat_lag_ok(keys: Sequence[str], min_lag: int) -> bool:
    last: Dict[str, int] = {}
    for i, k in enumerate(keys):
        if k in last and i - last[k] < min_lag:
            return False
        last[k] = i
    return True


# ─────────────────────────────────────────────
#  1단계: 세트마다 추천 위치 정하기
# ─────────────────────────────────────────────


def assign_rec_positions(
    set_keys: Sequence[str], rng: random.Random, n_positions: int = None
) -> Dict[str, int]:
    """세트마다 추천 제품이 놓일 줄을 고르게 나눠 준다.

    세트 수가 줄 수로 나누어떨어지면 정확히 같은 수씩, 아니면 최대한 고르게
    나눈 뒤 섞는다.
    """
    n_pos = C.CANDIDATES_PER_SET if n_positions is None else n_positions
    keys = list(set_keys)
    rng.shuffle(keys)

    positions = [(i % n_pos) + 1 for i in range(len(keys))]
    rng.shuffle(positions)
    return dict(zip(keys, positions))


# ─────────────────────────────────────────────
#  2단계: 세트마다 정보원 배정
# ─────────────────────────────────────────────


def assign_sources(
    rec_positions: Dict[str, int],
    source_codes: Sequence[str],
    rng: random.Random,
    max_tries: int = 20000,
) -> Dict[str, List[str]]:
    """세트마다 서로 다른 정보원을 REPEATS_PER_SET개 배정한다.

    추천 위치가 같은 세트들을 한 묶음으로 보고, 묶음 안에서 정보원 순열을
    반복 수만큼 겹치지 않게 뽑는다. 그러면 정보원마다 위치 1·2·3을 같은 수씩
    맡게 되고, 전체를 합치면 시행 수도 고르게 떨어진다.
    """
    codes = list(source_codes)
    reps = C.REPEATS_PER_SET
    if reps > len(codes):
        raise DesignError(
            "반복 수(%d)가 정보원 수(%d)보다 많으면 같은 세트에 같은 정보원이 "
            "겹칩니다." % (reps, len(codes))
        )

    by_pos: Dict[int, List[str]] = {}
    for key, pos in rec_positions.items():
        by_pos.setdefault(pos, []).append(key)
    for keys in by_pos.values():
        keys.sort()

    for _ in range(max_tries):
        assignment: Dict[str, List[str]] = {}
        ok = True
        for pos in sorted(by_pos):
            keys = list(by_pos[pos])
            rng.shuffle(keys)

            # 반복 수만큼 순열을 뽑되, 같은 자리에서 겹치면 버린다
            perms = []
            for _ in range(reps):
                p = list(codes)
                rng.shuffle(p)
                perms.append(p)
            if any(len({p[i] for p in perms}) != reps for i in range(len(codes))):
                ok = False
                break

            for i, key in enumerate(keys):
                assignment[key] = [p[i % len(codes)] for p in perms]
        if ok:
            return assignment

    raise DesignError(
        "정보원 배정 조건을 만족하는 조합을 찾지 못했습니다. "
        "제품군 수, 세트 수, 정보원 수를 확인해 주세요."
    )


# ─────────────────────────────────────────────
#  3단계: 시행 순서 정하기
# ─────────────────────────────────────────────


def order_trials(
    trials: List[Trial], rng: random.Random, max_tries: int = 20000
) -> List[Trial]:
    """연속 제약과 반복 간격을 만족하는 순서로 늘어놓는다."""
    best: Optional[List[Trial]] = None
    for _ in range(max_tries):
        seq = list(trials)
        rng.shuffle(seq)
        if not _max_run_ok([t.source_code for t in seq], C.MAX_SAME_SOURCE_RUN):
            continue
        if not _max_run_ok([t.category_code for t in seq], C.MAX_SAME_CATEGORY_RUN):
            continue
        if not _repeat_lag_ok([t.set_key for t in seq], MIN_REPEAT_LAG):
            best = seq
            continue
        return seq

    if best is not None:
        # 반복 간격만 못 맞춘 경우. 나머지 제약은 지켜졌으니 그대로 쓴다.
        return best
    raise DesignError("시행 순서 제약을 만족하는 배열을 찾지 못했습니다.")


# ─────────────────────────────────────────────
#  전체 조립
# ─────────────────────────────────────────────


def _make_trial(
    cs: CandidateSet,
    rec_pos: int,
    extra: List[str],
    source: Source,
    repetition: int,
    block: str,
) -> Trial:
    rec = cs.candidates[rec_pos - 1]
    return Trial(
        trial_number=0,
        block=block,
        set_key=cs.set_key,
        category_code=cs.category_code,
        category_kr=cs.category_kr,
        set_id=cs.set_id,
        source_code=source.source_code,
        source_label=source.label,
        repetition=repetition,
        price=cs.price,
        rec_position=rec_pos,
        rec_brand=rec.brand,
        rec_detail=rec.detail.text,
        rec_detail_type=rec.detail.detail_type,
        candidate_brands=[c.brand for c in cs.candidates],
        candidate_details=[c.detail.text for c in cs.candidates],
        extra_lines=list(extra),
    )


def build_main_trials(
    sets: Sequence[CandidateSet],
    sources: Sequence[Source],
    detail_pools: Dict[str, List[Detail]],
    rng: random.Random,
) -> List[Trial]:
    """본 과제 시행을 만든다."""
    from .stimuli import extra_detail_lines

    by_key = {cs.set_key: cs for cs in sets}
    rec_positions = assign_rec_positions(sorted(by_key), rng)
    assignment = assign_sources(rec_positions, [s.source_code for s in sources], rng)
    source_of = {s.source_code: s for s in sources}

    trials: List[Trial] = []
    for set_key, codes in assignment.items():
        cs = by_key[set_key]
        rec_pos = rec_positions[set_key]
        # 같은 세트가 다시 나올 때 화면이 글자 그대로 같아야 한다.
        # 그래서 덧붙는 줄도 세트 단위로 한 번만 뽑는다.
        extra = extra_detail_lines(cs, detail_pools, rng)
        for rep, code in enumerate(codes, start=1):
            trials.append(
                _make_trial(cs, rec_pos, extra, source_of[code], rep, "main")
            )

    trials = order_trials(trials, rng)
    for i, t in enumerate(trials, start=1):
        t.trial_number = i
    return trials


def build_practice_trials(
    excluded_sets: Sequence[CandidateSet],
    detail_pools: Dict[str, List[Detail]],
    rng: random.Random,
    practice_label: str,
    n: int = None,
) -> List[Trial]:
    """연습 시행. 본 과제에서 빠진 제품군을 쓴다.

    정보원 라벨은 중립 문구 하나로 통일한다. 연습 때문에 특정 정보원만 더
    자주 보이는 일을 막으려는 것.
    """
    from .stimuli import extra_detail_lines

    n = C.N_PRACTICE_TRIALS if n is None else n
    dummy = Source("practice", practice_label, practice_label, "")
    pool = list(excluded_sets)
    rng.shuffle(pool)

    trials = []
    for i, cs in enumerate(pool[:n], start=1):
        rec_pos = rng.randint(1, len(cs.candidates))
        extra = extra_detail_lines(cs, detail_pools, rng)
        t = _make_trial(cs, rec_pos, extra, dummy, 1, "practice")
        t.trial_number = i
        trials.append(t)
    return trials


# ─────────────────────────────────────────────
#  사후 블록 순서
# ─────────────────────────────────────────────


def similarity_order(sources: Sequence[Source], rng: random.Random) -> List[tuple]:
    """유사도 쌍. 제시 순서와 좌우 위치를 함께 섞는다."""
    from .stimuli import source_pairs

    pairs = source_pairs(sources)
    rng.shuffle(pairs)
    return [(b, a) if rng.random() < 0.5 else (a, b) for a, b in pairs]


def phase_rating_order(
    sources: Sequence[Source], items: Sequence, rng: random.Random
) -> List[tuple]:
    """국면별 평정. 정보원 순서와 문항 순서를 둘 다 섞는다.

    한 정보원의 문항을 붙여서 낸다. 문항마다 정보원이 튀면 회상 프레임이
    끊어지기 때문.
    """
    src = list(sources)
    rng.shuffle(src)
    out = []
    for s in src:
        block = list(items)
        rng.shuffle(block)
        out.extend((s, item) for item in block)
    return out


def decision_first(participant_id: str) -> bool:
    """참가자 절반은 결정 단계를 먼저 답한다.

    ID 끝자리 숫자의 홀짝으로 가른다. 숫자가 없으면 글자 합으로 가른다.
    """
    digits = [ch for ch in str(participant_id) if ch.isdigit()]
    if digits:
        return int(digits[-1]) % 2 == 1
    return sum(ord(ch) for ch in str(participant_id)) % 2 == 1
