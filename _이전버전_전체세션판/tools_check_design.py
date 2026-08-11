# -*- coding: utf-8 -*-
"""설계 검사기. PsychoPy 없이 돌아간다.

가상의 참가자를 여러 명 만들어 시행 배치를 뽑고, 지켜야 할 조건이 전부 지켜지는지
센다. 자극 CSV나 config 숫자를 고친 뒤에는 이걸 먼저 돌려 보는 것이 좋다.

    python tools_check_design.py [반복수]
"""

from __future__ import annotations

import collections
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from gptc import config as C
from gptc import design, stimuli


FAILS = []


def check(condition: bool, message: str) -> None:
    if not condition:
        FAILS.append(message)


def run_one(seed: int, sources, categories, pools) -> dict:
    rng = random.Random(seed)
    all_sets = stimuli.build_candidate_sets(categories, pools, rng)

    codes = sorted(categories)
    excluded = rng.sample(codes, C.N_EXCLUDED_CATEGORIES)
    main_sets = [cs for cs in all_sets if cs.category_code not in excluded]

    trials = design.build_main_trials(main_sets, sources, pools, rng)

    # ── 개수 ──────────────────────────────────────────────────
    expected = len(main_sets) * C.REPEATS_PER_SET
    check(len(trials) == expected, "시행 수 %d != %d" % (len(trials), expected))

    # ── 정보원별 균형 ─────────────────────────────────────────
    per_source = collections.Counter(t.source_code for t in trials)
    check(
        len(set(per_source.values())) == 1,
        "정보원별 시행 수가 고르지 않음: %s" % dict(per_source),
    )
    check(len(per_source) == len(sources), "안 쓰인 정보원이 있음: %s" % dict(per_source))

    pos_by_source = collections.defaultdict(collections.Counter)
    for t in trials:
        pos_by_source[t.source_code][t.rec_position] += 1
    for code, counts in pos_by_source.items():
        spread = max(counts.values()) - min(counts.values())
        check(
            len(counts) == C.CANDIDATES_PER_SET and spread <= 1,
            "%s 추천 위치가 고르지 않음: %s" % (code, dict(counts)),
        )

    # ── 세트별 조건 ───────────────────────────────────────────
    by_set = collections.defaultdict(list)
    for t in trials:
        by_set[t.set_key].append(t)

    for key, group in by_set.items():
        check(len(group) == C.REPEATS_PER_SET,
              "%s 등장 횟수 %d != %d" % (key, len(group), C.REPEATS_PER_SET))
        first = group[0]
        check(len({t.source_code for t in group}) == len(group),
              "%s 같은 정보원이 두 번" % key)
        for t in group[1:]:
            check(t.rec_brand == first.rec_brand, "%s 추천 제품이 다름" % key)
            check(t.rec_position == first.rec_position, "%s 추천 위치가 다름" % key)
            check(t.price == first.price, "%s 가격이 다름" % key)
            check(t.candidate_brands == first.candidate_brands, "%s 후보 배열이 다름" % key)
            check(t.candidate_details == first.candidate_details, "%s 후보 특징이 다름" % key)
            check(t.extra_lines == first.extra_lines, "%s 상세 항목이 다름" % key)

    # ── 세트 안 구성 ──────────────────────────────────────────
    for cs in all_sets:
        brands = [c.brand for c in cs.candidates]
        details = [c.detail.text for c in cs.candidates]
        check(len(set(brands)) == len(brands), "%s 브랜드명 중복" % cs.set_key)
        check(len(set(details)) == len(details), "%s 특징 중복" % cs.set_key)
        cat = categories[cs.category_code]
        check(cat.price_low <= cs.price <= cat.price_high,
              "%s 가격 %d이 범위 밖" % (cs.set_key, cs.price))

    all_brands = [c.brand for cs in all_sets for c in cs.candidates]
    check(len(set(all_brands)) == len(all_brands), "참가자 안에서 브랜드명 중복")
    check(all(4 <= len(b) <= 5 and b.isalpha() for b in all_brands),
          "알파벳 4~5자가 아닌 브랜드명이 있음")

    # 결정 국면에 같은 문구가 두 번 나오지 않아야 한다
    for t in trials:
        lines = [t.rec_detail] + t.extra_lines
        check(len(set(lines)) == len(lines), "%s 결정 국면 문구 중복" % t.set_key)

    # ── 연속 제약 ─────────────────────────────────────────────
    def max_run(seq):
        best = run = 1
        for i in range(1, len(seq)):
            run = run + 1 if seq[i] == seq[i - 1] else 1
            best = max(best, run)
        return best

    src_run = max_run([t.source_code for t in trials])
    cat_run = max_run([t.category_code for t in trials])
    check(src_run <= C.MAX_SAME_SOURCE_RUN, "같은 정보원 %d연속" % src_run)
    check(cat_run <= C.MAX_SAME_CATEGORY_RUN, "같은 제품군 %d연속" % cat_run)

    last, min_lag = {}, 99
    for i, t in enumerate(trials):
        if t.set_key in last:
            min_lag = min(min_lag, i - last[t.set_key])
        last[t.set_key] = i
    return {"min_lag": min_lag, "n_trials": len(trials)}


def main() -> int:
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 200

    sources = stimuli.load_sources()
    categories = stimuli.load_categories()
    pools = stimuli.load_details()

    kept = len(categories) - C.N_EXCLUDED_CATEGORIES
    expected = kept * C.SETS_PER_CATEGORY * C.REPEATS_PER_SET
    print("정보원 %d종, 제품군 %d개 (제외 %d -> %d개 사용)"
          % (len(sources), len(categories), C.N_EXCLUDED_CATEGORIES, kept))
    print("특징 풀   : 제품군당 %s개"
          % sorted({len(v) for v in pools.values()}))
    print("예상 시행 : %d개 x %d세트 x %d회 = %d시행, 정보원당 %.1f"
          % (kept, C.SETS_PER_CATEGORY, C.REPEATS_PER_SET, expected,
             expected / len(sources)))

    check(expected % len(sources) == 0,
          "시행 수 %d가 정보원 %d종으로 안 나뉨" % (expected, len(sources)))
    check(all(c.major_class != "FOOD" for c in categories.values()),
          "FOOD 제품군이 남아 있음")
    lows = [c.price_low for c in categories.values()]
    highs = [c.price_high for c in categories.values()]
    print("가격 범위 : %s ~ %s원" % (format(min(lows), ","), format(max(highs), ",")))
    check(min(lows) >= 30000, "30,000원 미만 범위가 있음: %d" % min(lows))
    check(max(highs) <= 50000, "50,000원 초과 범위가 있음: %d" % max(highs))

    lags = []
    for seed in range(n):
        lags.append(run_one(seed, sources, categories, pools)["min_lag"])

    print("\n가상 참가자 %d명 배치 생성 완료" % n)
    print("같은 세트 재등장 최소 간격: 중앙값 %d, 최소 %d 시행"
          % (sorted(lags)[len(lags) // 2], min(lags)))

    if FAILS:
        print("\n실패 %d건" % len(FAILS))
        for msg in sorted(set(FAILS))[:20]:
            print("  x", msg)
        return 1

    print("\n모든 조건 통과")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
