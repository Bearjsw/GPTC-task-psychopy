# -*- coding: utf-8 -*-
"""브랜드명 후보를 만들어 stim/brands.csv에 넣는다.

자음과 모음이 번갈아 오는 구조로만 만들어서 전부 읽힌다. 무작위 알파벳을
그 자리에서 뽑던 방식은 버렸다. 연구 전체로 보면 2만 개가 만들어지는데
그중 절반 가까이가 모음이 없어 읽히지 않았고, 무엇보다 사람이 한 번도 보지
않은 이름이 참가자 화면에 뜨는 구조였다.

여기서 나온 목록은 **사람이 한 번 훑어야 한다.** 어색하거나 뜻이 읽히거나
불쾌한 것은 그 행을 지우면 된다. 72개 이상 남으면 실험은 돌아간다.

    python tools_make_brands.py [개수] [시드]
"""

from __future__ import annotations

import csv
import io
import os
import random
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "stim", "brands.csv")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# 한글 화자가 읽기 쉬운 소리로만 골랐다. q, x, w, y, j는 뺐다.
ONSET = list("bdfgklmnprstv") + ["br", "cl", "dr", "fl", "gr", "pl", "tr", "kr", "st"]
VOWEL = ["a", "e", "i", "o", "u", "ia", "io", "ea", "au", "ei"]
CODA = ["", "", "", "n", "r", "l", "s", "t", "m", "na", "no", "ra", "lo", "va", "ne"]

# 걸러 내기. 최종 방어선은 사람 눈이고 이건 1차 체다.
BLOCK = {
    "ass", "fuk", "fuc", "shi", "sht", "cok", "cok", "dik", "cun", "nig",
    "rap", "kkk", "sex", "pis", "dam", "hel", "naz", "jap", "chi", "gay",
    "hom", "ret", "spa", "wop", "kik", "gyp", "tit", "bum", "gut", "pus",
}
# 실재하는 상표와 겹치면 안 된다
REAL = {
    "sony", "bose", "anker", "logi", "nike", "puma", "fila", "gucci",
    "prada", "dior", "chanel", "apple", "samsung", "lg", "dell", "asus",
    "lotte", "cj", "orion", "kolon", "kirin", "sanyo", "casio", "seiko",
}


def make_pool(n, rng):
    pool, seen = [], set()
    guard = 0
    while len(pool) < n and guard < n * 400:
        guard += 1
        syllables = rng.choice((2, 2, 3))
        s = "".join(rng.choice(ONSET) + rng.choice(VOWEL) for _ in range(syllables))
        s += rng.choice(CODA)

        if not 4 <= len(s) <= 7:
            continue
        if re.search(r"[bcdfgklmnprstv]{3}", s):
            continue                                    # 자음 3연속
        if re.search(r"([aeiou])\1", s):
            continue                                    # 같은 모음 연속
        if any(b in s for b in BLOCK):
            continue
        if any(r in s or s in r for r in REAL):
            continue
        if s in seen:
            continue
        # 앞 두 글자가 같은 이름이 몰리면 화면에서 헷갈린다
        if sum(1 for p in pool if p[:2].lower() == s[:2]) >= 3:
            continue
        seen.add(s)
        pool.append(s.capitalize())
    return sorted(pool)


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 150
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 20260812
    pool = make_pool(n, random.Random(seed))

    with io.open(OUT, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["brand"])
        for b in pool:
            w.writerow([b])

    print("%d개 생성 -> %s" % (len(pool), OUT))
    print("\n검수하세요. 어색하거나 뜻이 읽히거나 불쾌한 행은 지우면 됩니다.")
    print("72개 이상 남으면 실험은 돌아갑니다.\n")
    for i in range(0, min(len(pool), 40), 5):
        print("   " + "   ".join("%-9s" % b for b in pool[i:i + 5]))
    if len(pool) > 40:
        print("   ... 나머지 %d개는 CSV에서" % (len(pool) - 40))


if __name__ == "__main__":
    main()
