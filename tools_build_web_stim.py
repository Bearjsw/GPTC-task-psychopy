# -*- coding: utf-8 -*-
"""stim/ 과 stim_0818/ 의 CSV를 web/gptc_stim.js 로 굽는다.

브라우저는 file:// 에서 CSV를 못 읽고, http로 띄워도 fetch가 한 번 더 도는 만큼
시작이 늦다. 자극을 JS 파일에 그대로 박아 두면 그 문제가 사라진다.

    python tools_build_web_stim.py

자극 CSV를 고쳤으면 이걸 다시 돌려야 웹판에 반영된다.
"""

from __future__ import annotations

import csv
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "web", "gptc_stim.js")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

VARIANTS = [
    ("classic", "stim", False),        # 기존판. 결정 국면이 특징 세 줄
    ("list0818", "stim_0818", True),   # 0818판. 결정 국면이 요약 문장 한 줄
]


def read(folder, name):
    path = os.path.join(ROOT, folder, name)
    with io.open(path, encoding="utf-8-sig", newline="") as fh:
        return [r for r in csv.DictReader(fh)
                if any((v or "").strip() for v in r.values())]


def build(folder, with_phase2):
    cats = []
    for r in read(folder, "categories.csv"):
        cats.append({
            "code": r["category_code"].strip(),
            "kr": r["category_kr"].strip(),
            "major": r["major_class"].strip(),
            "low": int(r["price_low"]),
            "high": int(r["price_high"]),
            "block": (r.get("block") or "main").strip().lower(),
        })

    details = {}
    for r in read(folder, "details.csv"):
        details.setdefault(r["category_code"].strip(), []).append(
            [r["detail_type"].strip().upper(), r["text"].strip()]
        )

    out = {
        "categories": cats,
        "details": details,
        "sources": [{"code": r["source_code"].strip(), "label": r["label"].strip()}
                    for r in read(folder, "sources.csv")],
        "brands": [r["brand"].strip() for r in read(folder, "brands.csv")
                   if r["brand"].strip()],
    }
    if with_phase2:
        phase2 = {}
        for r in read(folder, "phase2.csv"):
            phase2.setdefault(r["category_code"].strip(), {})[
                r["detail_type"].strip().upper()] = r["text"].strip()
        out["phase2"] = phase2
    return out


def main():
    data = {}
    for key, folder, with_phase2 in VARIANTS:
        data[key] = build(folder, with_phase2)
        cats = data[key]["categories"]
        n_main = sum(1 for c in cats if c["block"] == "main")
        n_prac = len(cats) - n_main
        print("%-10s %s/  본 과제 %d개 · 연습 %d개 · 브랜드 %d개"
              % (key, folder, n_main, n_prac, len(data[key]["brands"])))

    body = json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("// 자동 생성 파일. 직접 고치지 말고 stim/ 이나 stim_0818/ 의 CSV를\n")
        fh.write("// 고친 뒤 python tools_build_web_stim.py 를 다시 돌린다.\n\n")
        fh.write("export const STIM = ")
        fh.write(body)
        fh.write(";\n")
    print("\n%s  (%.0f KB)" % (OUT, os.path.getsize(OUT) / 1024.0))


if __name__ == "__main__":
    main()
