# -*- coding: utf-8 -*-
"""화면 문구 미리보기.

참가자가 실제로 볼 글자를 터미널에 그려 본다. 자극 문구를 고친 뒤 줄이 너무
길지 않은지 확인하는 용도다.

    python tools_preview.py [시드]
"""

from __future__ import annotations

import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from tools_check_design import T          # psychopy 없이 설계 부분만 가져온다

CFG = T.CFG
WIDTH = 66


def box(lines, title=""):
    print("┌" + "─" * WIDTH + "┐")
    if title:
        print("│" + title.center(WIDTH) + "│")
        print("├" + "─" * WIDTH + "┤")
    for line in lines:
        print("│" + line.center(WIDTH) + "│")
    print("└" + "─" * WIDTH + "┘")


def main():
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    rng = random.Random(seed)

    sources, categories, details, brands = T.load_stimuli()
    all_sets = T.build_sets(categories, details, brands, rng)

    main_sets = [cs for cs in all_sets if cs["block"] == "main"]
    practice_sets = [cs for cs in all_sets if cs["block"] == "practice"]
    _, trials = T.build_trials(main_sets, practice_sets, sources, rng)

    by_set = {}
    for i, t in enumerate(trials):
        by_set.setdefault(t["set_key"], []).append((i + 1, t))
    pair = by_set[sorted(by_set)[0]]

    prac = [c["category_kr"] for c in categories if c["block"] == "practice"]
    print("\n본 과제 제품군 %d개. 연습 전용: %s" % (len(main_sets) //
          CFG["sets_per_category"], ", ".join(prac)))
    print("아래 두 시행은 같은 세트다. 정보원 라벨 말고는 글자가 같아야 한다.\n")

    for number, t in pair:
        lines = [t["source_label"], ""]
        lines += ["%s %s  -  %s" % (b, t["category_kr"], d)
                  for b, d in zip(t["brands"], t["details"])]
        lines += ["", "이 중에 구매할 만한 게 있어 보입니까?",
                  "①  ②  ③  ④  ⑤  ⑥  ⑦",
                  "전혀 없어 보인다%s매우 있어 보인다" % (" " * 12)]
        box(lines, "정보 국면 · 시행 %d" % number)

        lines = [t["source_label"], "",
                 "%s %s" % (t["rec_brand"], t["category_kr"]),
                 "{:,}원".format(t["price"]), ""]
        lines += ["· " + d for d in [t["rec_detail"]] + t["extra"]]
        lines += ["", "이 제품을 구매하시겠습니까?", "[ 구매한다 ]      [ 구매하지 않는다 ]"]
        box(lines, "결정 국면 · %d번째 줄 추천 · %s"
                   % (t["rec_position"], t["rec_detail_type"]))
        print()


if __name__ == "__main__":
    main()
