# -*- coding: utf-8 -*-
"""화면 확인용 데모. 36시행을 다 돌리지 않고 종류별로 하나씩만 보여 준다.

목업이 아니라 run_session2.py가 쓰는 코드 경로를 그대로 탄다. 여기서 보이는
화면이 실제 실험 화면이다.

    python tools_demo_screens.py            창 모드
    python tools_demo_screens.py --full     전체 화면

넘기기는 스페이스바, 응답은 좌우 + Enter, 빠져나가기는 Esc 누르고 Y.
데이터는 data_demo/ 로 빠진다.
"""

from __future__ import annotations

import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gptc import config as C                                       # noqa: E402

C.FULLSCREEN = "--full" in sys.argv
C.DATA_DIR = os.path.join(C.ROOT, "data_demo")

from psychopy import core, visual                                  # noqa: E402

from gptc import design, postblocks, stimuli, task                 # noqa: E402
from gptc.recorder import Recorder                                 # noqa: E402
from gptc.widgets import ParticipantQuit, Screen, resolve_font     # noqa: E402


BANNER = """화면 확인용 데모입니다.

  스페이스바   다음으로
  ← →         선택 옮기기
  Enter        선택 확정
  Esc 뒤 Y     빠져나가기

계속하려면 스페이스바를 누르세요."""


def note(screen: Screen, text: str) -> None:
    """다음에 무엇이 나오는지 알려 주는 안내 카드."""
    screen.wait_for_space(
        [screen.text(text + "\n\n(스페이스바)", height=C.H_INSTRUCTION, wrap=1.5)]
    )


def main() -> None:
    rng = random.Random(20260811)
    recorder = Recorder("DEMO")

    sources = stimuli.load_sources()
    categories = stimuli.load_categories()
    survey_blocks = stimuli.load_survey_items()
    all_sets = stimuli.load_candidate_sets()
    stimuli.randomize_brand_names(all_sets, rng)

    # 데모라 제외 제품군을 임의로 정한다. 실제로는 세션 1이 정한다.
    codes = sorted({cs.category_code for cs in all_sets})
    excluded = rng.sample(codes, C.N_EXCLUDED_CATEGORIES)
    main_sets = [cs for cs in all_sets if cs.category_code not in excluded]

    set_ranks = {}
    for cs in main_sets:
        brands = [b.brand for b in cs.brands]
        rng.shuffle(brands)
        set_ranks[cs.set_key] = brands

    trials = design.build_main_trials(main_sets, sources, categories, set_ranks, rng)

    win = visual.Window(
        size=C.WIN_SIZE,
        fullscr=C.FULLSCREEN,
        color=C.BG_COLOR,
        units=C.UNITS,
        allowGUI=not C.FULLSCREEN,
        winType="pyglet",
    )
    win.mouseVisible = not C.FULLSCREEN
    screen = Screen(win, resolve_font())
    print("쓰는 폰트:", screen.font)

    try:
        screen.instruction(BANNER)

        # 1. 과제 안내 ------------------------------------------------
        screen.instruction(C.TXT_WELCOME)
        screen.instruction(C.TXT_KEYS)

        # 2. 본 시행 2개 ----------------------------------------------
        # 같은 세트가 두 번 나오는 짝을 골라 붙여 보여 준다. 정보원 라벨 말고는
        # 글자가 같아야 한다는 점을 눈으로 확인하려는 것.
        by_set = {}
        for t in trials:
            by_set.setdefault(t.set_key, []).append(t)
        pair = by_set[sorted(by_set)[0]]

        runner = task.TaskRunner(
            screen, {cs.set_key: cs for cs in all_sets}, recorder, rng
        )
        for i, trial in enumerate(pair, start=1):
            note(
                screen,
                "본 시행 %d/2\n\n같은 후보 세트를 두 번 보여 줍니다.\n"
                "정보원 라벨 말고는 글자가 같습니다.\n\n"
                "정보원 %s · 추천은 참가자 기준 %d순위"
                % (i, trial.source_label, trial.rec_rank),
            )
            runner.run_trial(trial)

        # 3. 사후 블록 한 문항씩 ---------------------------------------
        note(screen, "사후 ①  유사도 15쌍\n\n한 문항만 보여 드립니다.")
        postblocks.run_similarity(screen, sources[:2], recorder, rng)

        note(screen, "사후 ②  국면별 평정\n\n정보 단계 안내문과 문항 하나입니다.")
        postblocks.run_phase_ratings(
            screen,
            "info",
            sources[:1],
            survey_blocks["phase_rating"][:1],
            recorder,
            rng,
            block_position=1,
        )

        note(screen, "사후 ③  처리 동기")
        postblocks.run_processing(screen, survey_blocks["processing"][:1], recorder, rng)

        screen.instruction("데모가 끝났습니다.\n\n스페이스바를 누르면 닫힙니다.")

    except ParticipantQuit:
        pass
    finally:
        recorder.close(completed=True, note="demo")
        win.mouseVisible = True
        win.close()
        core.quit()


if __name__ == "__main__":
    main()
