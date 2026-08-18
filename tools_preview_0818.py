# -*- coding: utf-8 -*-
"""화면 문구 미리보기 · 0818 제품 리스트판.

참가자가 실제로 볼 글자를 터미널에 그려 본다. 자극 문구를 고친 뒤 줄이 너무
길지 않은지 확인하는 용도다. 결정 국면 문장은 화면에서 자동으로 접히므로
여기서도 접어서 보여 준다.

    python tools_preview_0818.py [시드] [제품군코드]
"""

from __future__ import annotations

import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from tools_check_design_0818 import T     # psychopy 없이 설계 부분만 가져온다

CFG = T.CFG
WIDTH = 66
WRAP = 46          # 결정 국면 문장이 화면에서 접히는 대강의 글자 수


def box(lines, title=""):
    print("┌" + "─" * WIDTH + "┐")
    if title:
        print("│" + title.center(WIDTH) + "│")
        print("├" + "─" * WIDTH + "┤")
    for line in lines:
        print("│" + line.center(WIDTH) + "│")
    print("└" + "─" * WIDTH + "┘")


def fold(text, width=WRAP):
    out, line = [], ""
    for word in text.split():
        if line and len(line) + 1 + len(word) > width:
            out.append(line)
            line = word
        else:
            line = "%s %s" % (line, word) if line else word
    if line:
        out.append(line)
    return out


def screens(t):
    lines = [t["source_label"], ""]
    lines += ["%s %s  -  %s" % (b, t["category_kr"], d)
              for b, d in zip(t["brands"], t["details"])]
    lines += ["", "이 중에 구매할 만한 게 있어 보입니까?",
              "①  ②  ③  ④  ⑤  ⑥  ⑦",
              "전혀 없어 보인다%s매우 있어 보인다" % (" " * 12)]
    info = lines

    lines = [t["source_label"], "",
             "%s %s" % (t["rec_brand"], t["category_kr"]),
             "{:,}원".format(t["price"]), ""]
    lines += fold(t["phase2"])
    lines += ["", "이 제품을 구매하시겠습니까?",
              "[ 구매한다 ]      [ 구매하지 않는다 ]"]
    return info, lines


def main():
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    want = sys.argv[2] if len(sys.argv) > 2 else None
    rng = random.Random(seed)

    sources, categories, details, phase2, brands = T.load_stimuli()
    all_sets = T.build_sets(categories, details, phase2, brands, rng)
    main_sets = [cs for cs in all_sets if cs["block"] == "main"]
    practice_sets = [cs for cs in all_sets if cs["block"] == "practice"]
    _, trials = T.build_trials(main_sets, practice_sets, sources, rng)

    by_set = {}
    for i, t in enumerate(trials):
        by_set.setdefault(t["set_key"], []).append((i + 1, t))

    keys = sorted(by_set)
    if want:
        keys = [k for k in keys if k.startswith(want)]
        if not keys:
            raise SystemExit("그런 제품군이 없습니다: %s" % want)
    pair = by_set[keys[0]]

    longest = max(phase2.values(), key=lambda d: max(len(v) for v in d.values()))
    print("\n제품군 %d개를 전부 쓴다. 빼는 제품군은 없다." % len(main_sets))
    print("결정 국면 문장 최대 길이 %d자 (%d자를 넘으면 두 줄로 접힌다)"
          % (max(len(v) for v in longest.values()), WRAP))
    print("아래 두 시행은 같은 세트다. 정보원 라벨 말고는 글자가 같아야 한다.\n")

    for number, t in pair:
        info, decision = screens(t)
        box(info, "정보 국면 · 시행 %d · %s" % (number, t["major_class"]))
        box(decision, "결정 국면 · %d번째 줄 추천 · %s"
                      % (t["rec_position"], t["rec_detail_type"]))
        print()


if __name__ == "__main__":
    main()
