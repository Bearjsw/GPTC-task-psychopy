# -*- coding: utf-8 -*-
"""과제 화면을 한 장씩 PNG로 뽑는다. 보고서에 넣을 그림용.

GPTC_task.py를 그대로 읽어 쓰기 때문에 여기서 나온 그림이 실제 화면이다.

    python tools_capture_screens.py [저장폴더]
"""

from __future__ import annotations

import io
import os
import random
import sys

if not sys.flags.utf8_mode:
    import subprocess

    sys.exit(subprocess.call([sys.executable, "-X", "utf8"] + sys.argv))

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
sys.stdout.reconfigure(encoding="utf-8")

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "screens")
os.makedirs(OUT, exist_ok=True)


def load_task():
    """GPTC_task.py를 창 모드로 읽어 들인다. main()은 돌리지 않는다."""
    src = io.open(os.path.join(ROOT, "GPTC_task.py"), encoding="utf-8").read()
    src = src.replace("ARGS = sys.argv[1:]", 'ARGS = ["--windowed"]')
    src = src.replace('if __name__ == "__main__":\n    main()', "")
    ns = {"__name__": "gptc_capture", "__file__": os.path.join(ROOT, "GPTC_task.py")}
    exec(compile(src, "GPTC_task.py", "exec"), ns)
    return ns


T = load_task()
CFG = T["CFG"]

from psychopy import visual  # noqa: E402


def shot(win, name, stims):
    for s in stims:
        s.draw()
    win.flip()
    win.getMovieFrame()
    img = win.movieFrames.pop()
    path = os.path.join(OUT, name + ".png")
    img.convert("RGB").save(path)
    print("  저장:", name + ".png")


def main():
    rng = random.Random(7)
    sources, categories, details, brands = T["load_stimuli"]()
    all_sets = T["build_sets"](categories, details, brands, rng)

    codes = sorted({c["category_code"] for c in categories})
    excluded = rng.sample(codes, CFG["n_excluded"])
    main_sets = [cs for cs in all_sets if cs["category_code"] not in excluded]
    practice_sets = [cs for cs in all_sets if cs["category_code"] in excluded]
    practice, trials = T["build_trials"](main_sets, practice_sets, sources, rng)

    # 같은 세트가 두 번 나오는 짝을 골라 둔다. 라벨만 다르다는 것을 보이려는 것.
    by_set = {}
    for t in trials:
        by_set.setdefault(t["set_key"], []).append(t)
    pair = by_set[sorted(by_set)[0]]

    win = visual.Window(size=(1280, 800), fullscr=False, color=CFG["bg_color"],
                        units="height", allowGUI=False, winType="pyglet")
    win.mouseVisible = False
    font = CFG["font_candidates"][0]
    try:
        from psychopy.visual.textbox2.fontmanager import FontManager

        avail = set(FontManager().getFontFamilyNames())
        font = next((f for f in CFG["font_candidates"] if f in avail), font)
    except Exception:
        pass
    disp = T["Display"](win, font, rng)
    print("폰트:", font)

    def instr(body):
        return [disp.text(body, pos=(0, 0.02), height=CFG["h_instruction"], wrap=1.5)]

    # ── 안내 화면 ────────────────────────────────────────────
    shot(win, "01_안내_과제소개", instr(T["TXT_WELCOME"]))
    shot(win, "02_안내_응답방법", instr(T["TXT_KEYS"]))
    shot(win, "03_안내_연습", instr(T["TXT_PRACTICE"]))
    shot(win, "04_고정점", [disp.fix_stim])

    # ── 정보 국면 ───────────────────────────────────────────
    t = pair[0]
    info = T["info_stims"](disp, t)
    shot(win, "05_정보국면_자극", info)

    disp.question.text = T["Q_INFO"]
    disp.left_desc.text = T["Q_INFO_LEFT"]
    disp.right_desc.text = T["Q_INFO_RIGHT"]
    disp._paint(None)
    shot(win, "06_정보국면_평정_미선택", disp._scale_stims(info))
    disp._paint(4)
    shot(win, "07_정보국면_평정_선택", disp._scale_stims(info))

    # ── 결정 국면 ───────────────────────────────────────────
    dec = T["decision_stims"](disp, t)
    shot(win, "08_결정국면_자극", dec)

    disp.binary_prompt.text = T["Q_BINARY"]
    shot(win, "09_결정국면_구매선택",
         list(dec) + [disp.binary_prompt] + disp.binary_labels)
    shot(win, "10_결정국면_구매선택_선택",
         list(dec) + [disp.binary_prompt] + disp.binary_labels + [disp.binary_boxes[0]])

    disp.question.text = T["Q_INTENT"]
    disp.left_desc.text = T["Q_INTENT_LEFT"]
    disp.right_desc.text = T["Q_INTENT_RIGHT"]
    disp._paint(5)
    shot(win, "11_결정국면_구매의향", disp._scale_stims(dec))

    # ── 같은 세트, 다른 정보원 ───────────────────────────────
    # 라벨 말고는 글자가 같다는 것을 나란히 보이려는 그림
    shot(win, "12_같은세트_정보원A", T["info_stims"](disp, pair[0]))
    shot(win, "13_같은세트_정보원B", T["info_stims"](disp, pair[1]))

    # ── 나머지 ──────────────────────────────────────────────
    shot(win, "14_휴식", instr(T["TXT_BREAK"]))
    shot(win, "15_종료", instr(T["TXT_END"]))
    shot(win, "16_일시정지", [disp.pause_stim])

    win.close()
    print("\n%s 에 %d장" % (OUT, len(os.listdir(OUT))))
    print("정보원 짝: %s / %s" % (pair[0]["source_label"], pair[1]["source_label"]))


if __name__ == "__main__":
    main()
