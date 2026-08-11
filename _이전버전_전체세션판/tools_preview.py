# -*- coding: utf-8 -*-
"""화면 문구 미리보기. PsychoPy 없이 돌아간다.

실제로 참가자가 볼 글자를 터미널에 그려 본다. 자극 문구를 고친 뒤 줄이 너무
길지 않은지, 조사가 제대로 붙었는지 확인하는 용도다.

    python tools_preview.py [시드]
"""

from __future__ import annotations

import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from gptc import config as C
from gptc import design, stimuli

WIDTH = 62


def box(lines, title=""):
    print("┌" + "─" * WIDTH + "┐")
    if title:
        print("│" + title.center(WIDTH) + "│")
        print("├" + "─" * WIDTH + "┤")
    for line in lines:
        print("│" + line.center(WIDTH) + "│")
    print("└" + "─" * WIDTH + "┘")


def main() -> None:
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    rng = random.Random(seed)

    sources = stimuli.load_sources()
    categories = stimuli.load_categories()
    pools = stimuli.load_details()
    all_sets = stimuli.build_candidate_sets(categories, pools, rng)

    excluded = rng.sample(sorted(categories), C.N_EXCLUDED_CATEGORIES)
    main_sets = [cs for cs in all_sets if cs.category_code not in excluded]
    trials = design.build_main_trials(main_sets, sources, pools, rng)

    # 같은 세트가 두 번 나오는 짝을 골라 보여 준다. 정보원 라벨만 달라야 한다.
    by_set = {}
    for t in trials:
        by_set.setdefault(t.set_key, []).append(t)
    demo_key = sorted(by_set)[0]
    pair = by_set[demo_key]

    print("\n제외 제품군: %s" % ", ".join(excluded))
    print("아래 두 시행은 같은 세트다. 정보원 라벨 말고는 글자가 같아야 한다.\n")

    for t in pair:
        lines = [t.source_label, t.category_kr, ""]
        lines += ["%s  -  %s" % (b, d)
                  for b, d in zip(t.candidate_brands, t.candidate_details)]
        lines += ["", C.Q_INFO_PHASE, "①  ②  ③  ④  ⑤  ⑥  ⑦",
                  "%s%s%s" % (C.Q_INFO_LEFT, " " * 14, C.Q_INFO_RIGHT)]
        box(lines, "정보 국면 · 시행 %d" % t.trial_number)

        lines = [t.source_label, t.category_kr, "",
                 t.rec_brand, stimuli.format_price(t.price), ""]
        lines += ["· " + d for d in [t.rec_detail] + t.extra_lines]
        lines += ["", C.Q_DECISION_BINARY,
                  "[ %s ]        [ %s ]" % (C.OPT_BUY, C.OPT_NOBUY)]
        box(lines, "결정 국면 · %d번째 줄 추천 · %s"
                   % (t.rec_position, t.rec_detail_type))
        print()

    # 사후 문항에 조사가 제대로 붙는지
    items = stimuli.load_survey_items()["phase_rating"]
    print("\n국면별 평정 문항 · 조사 처리 확인\n")
    for src in sources:
        name = src.short_name
        print("  [%s]" % name)
        for item in items[:2]:
            print("     " + item.rendered(name))
        print()



if __name__ == "__main__":
    main()
