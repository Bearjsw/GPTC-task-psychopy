# -*- coding: utf-8 -*-
"""설계 검사기.

가상의 참가자를 여러 명 만들어 시행 배치를 뽑고, 지켜야 할 조건이 전부
지켜지는지 센다. 자극 CSV나 GPTC_task.py의 CFG 숫자를 고친 뒤에는 이걸 먼저
돌려 보는 것이 좋다.

    python tools_check_design.py [반복수]
"""

from __future__ import annotations

import collections
import importlib.util
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def load_task_module():
    """GPTC_task.py에서 설계 부분만 가져온다.

    그 파일을 그냥 import하면 psychopy까지 딸려 올라온다. 여기서 필요한 것은
    CFG와 무작위화 함수뿐이라, psychopy import 줄을 빼고 읽어 들인다.
    """
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "GPTC_task.py")
    with open(path, encoding="utf-8") as fh:
        src = fh.read()
    src = src.replace("from psychopy import core, data, event, gui, visual", "")
    src = src.replace('if not sys.flags.utf8_mode:', 'if False:')
    # 화면과 응답 부분은 psychopy가 있어야 하므로 잘라 낸다
    cut = src.index("# ─────────────────────────────────────────────\n#  화면")
    src = src[:cut]

    module = importlib.util.module_from_spec(
        importlib.util.spec_from_loader("gptc_task_design", loader=None)
    )
    module.__file__ = path
    exec(compile(src, path, "exec"), module.__dict__)
    return module


T = load_task_module()
CFG = T.CFG
FAILS = []


def check(condition, message):
    if not condition:
        FAILS.append(message)


def run_one(seed, sources, categories, details, brands):
    rng = random.Random(seed)
    all_sets = T.build_sets(categories, details, brands, rng)

    main_sets = [cs for cs in all_sets if cs["block"] == "main"]
    practice_sets = [cs for cs in all_sets if cs["block"] == "practice"]

    practice, trials = T.build_trials(main_sets, practice_sets, sources, rng)

    # ── 개수 ──────────────────────────────────────────────────
    expected = len(main_sets) * CFG["repeats_per_set"]
    check(len(trials) == expected, "시행 수 %d != %d" % (len(trials), expected))
    check(len(practice) == CFG["n_practice"],
          "연습 시행 %d != %d" % (len(practice), CFG["n_practice"]))
    main_codes = {cs["category_code"] for cs in main_sets}
    check(not any(t["category_code"] in main_codes for t in practice),
          "연습에 본 과제 제품군이 섞임")

    # ── 정보원별 균형 ─────────────────────────────────────────
    per_source = collections.Counter(t["source_code"] for t in trials)
    check(len(set(per_source.values())) == 1,
          "정보원별 시행 수가 고르지 않음: %s" % dict(per_source))
    check(len(per_source) == len(sources),
          "안 쓰인 정보원이 있음: %s" % dict(per_source))

    pos_by_source = collections.defaultdict(collections.Counter)
    for t in trials:
        pos_by_source[t["source_code"]][t["rec_position"]] += 1
    for code, counts in pos_by_source.items():
        spread = max(counts.values()) - min(counts.values())
        check(len(counts) == CFG["candidates_per_set"] and spread <= 1,
              "%s 추천 위치가 고르지 않음: %s" % (code, dict(counts)))

    # ── 세트별 조건 ───────────────────────────────────────────
    by_set = collections.defaultdict(list)
    for t in trials:
        by_set[t["set_key"]].append(t)

    for key, group in by_set.items():
        check(len(group) == CFG["repeats_per_set"],
              "%s 등장 횟수 %d" % (key, len(group)))
        check(len({t["source_code"] for t in group}) == len(group),
              "%s 같은 정보원이 두 번" % key)
        first = group[0]
        for t in group[1:]:
            for field in ("rec_brand", "rec_position", "price", "brands",
                          "details", "extra"):
                check(t[field] == first[field], "%s %s가 다름" % (key, field))

    # ── 세트 안 구성 ──────────────────────────────────────────
    for cs in all_sets:
        check(len(set(cs["brands"])) == len(cs["brands"]), "%s 브랜드 중복" % cs["set_key"])
        check(len(set(cs["details"])) == len(cs["details"]), "%s 특징 중복" % cs["set_key"])
        cat = next(c for c in categories if c["category_code"] == cs["category_code"])
        check(int(cat["price_low"]) <= cs["price"] <= int(cat["price_high"]),
              "%s 가격 %d이 범위 밖" % (cs["set_key"], cs["price"]))

    brands = [b for cs in all_sets for b in cs["brands"]]
    check(len(set(brands)) == len(brands), "참가자 안에서 브랜드명 중복")
    check(all(b.isalpha() and 3 <= len(b) <= 10 for b in brands),
          "알파벳이 아니거나 길이가 이상한 브랜드명")
    import re as _re
    check(not any(_re.search(r"[bcdfgklmnprstvwxyz]{3}", b.lower()) for b in brands),
          "자음이 3개 넘게 붙은 브랜드명 (읽기 어렵다)")
    check(all(set(b.lower()) & set("aeiou") for b in brands),
          "모음이 없는 브랜드명")

    for t in trials:
        lines = [t["rec_detail"]] + t["extra"]
        check(len(set(lines)) == len(lines), "%s 결정 국면 문구 중복" % t["set_key"])

    # ── 연속 제약 ─────────────────────────────────────────────
    def max_run(seq):
        best = run = 1
        for i in range(1, len(seq)):
            run = run + 1 if seq[i] == seq[i - 1] else 1
            best = max(best, run)
        return best

    check(max_run([t["source_code"] for t in trials]) <= CFG["max_run"],
          "같은 정보원이 %d연속" % max_run([t["source_code"] for t in trials]))
    check(max_run([t["category_code"] for t in trials]) <= CFG["max_run"],
          "같은 제품군이 %d연속" % max_run([t["category_code"] for t in trials]))

    last, min_lag = {}, 99
    for i, t in enumerate(trials):
        if t["set_key"] in last:
            min_lag = min(min_lag, i - last[t["set_key"]])
        last[t["set_key"]] = i
    return min_lag


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    sources, categories, details, brands = T.load_stimuli()

    main_cats = [c for c in categories if c["block"] == "main"]
    prac_cats = [c for c in categories if c["block"] == "practice"]
    kept = len(main_cats)
    expected = kept * CFG["sets_per_category"] * CFG["repeats_per_set"]
    print("정보원 %d종, 본 과제 제품군 %d개, 연습 전용 %d개 (%s)"
          % (len(sources), kept, len(prac_cats),
             ", ".join(c["category_kr"] for c in prac_cats)))
    print("특징 풀   : 제품군당 %s개" % sorted({len(v) for v in details.values()}))
    print("브랜드 풀 : %d개 (필요 %d개)"
          % (len(brands),
             sum(T.sets_for(c) for c in categories) * CFG["candidates_per_set"]))
    print("예상 시행 : %d x %d세트 x %d회 = %d시행, 정보원당 %.1f"
          % (kept, CFG["sets_per_category"], CFG["repeats_per_set"],
             expected, expected / len(sources)))
    check(expected % len(sources) == 0,
          "시행 수 %d가 정보원 %d종으로 안 나뉨" % (expected, len(sources)))

    lows = [int(c["price_low"]) for c in categories]
    highs = [int(c["price_high"]) for c in categories]
    print("가격 범위 : %s ~ %s원" % (format(min(lows), ","), format(max(highs), ",")))
    check(min(lows) >= 30000, "30,000원 미만 범위가 있음")
    check(max(highs) <= 50000, "50,000원 초과 범위가 있음")
    check(all(c["major_class"] != "FOOD" for c in categories), "FOOD가 남아 있음")

    lags = [run_one(seed, sources, categories, details, brands) for seed in range(n)]
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
