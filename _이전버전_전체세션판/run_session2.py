# -*- coding: utf-8 -*-
"""GPTC 행동 선행실험 · 세션 2 · PsychoPy 실행 파일.

PsychoPy Coder에서 이 파일을 열고 Run 하거나, 터미널에서

    python run_session2.py

로 실행한다.

흐름
    참가자 정보 입력
    (세션 1 자료가 없으면) 제품군 관심도
    안내 -> 연습 -> 본 과제
    유사도 -> 국면 A 평정 -> 간섭 과제 -> 국면 B 평정 -> 처리 동기 -> 종료
"""

from __future__ import annotations

import os
import random
import sys

# 한국어 윈도우에서 PsychoPy가 import 단계에서 죽는 것을 막는다.
# psychopy.gui -> i18next가 한국어 번역 JSON을 열 때 인코딩을 지정하지 않아
# 시스템 기본값(cp949)으로 읽다가 UnicodeDecodeError를 낸다. UTF-8 모드가
# 꺼져 있으면 켜서 다시 띄운다.
#
# os.execv를 쓰지 않는다. 윈도우에서는 프로세스를 교체하는 대신 새로 띄우고
# 원본을 끝내 버려서, 부모가 곧바로 성공으로 끝나고 자식의 출력과 종료 코드가
# 사라진다. 오류가 나도 아무것도 안 남는다.
if not sys.flags.utf8_mode:
    import subprocess

    sys.exit(subprocess.call([sys.executable, "-X", "utf8"] + sys.argv))

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from psychopy import core, gui, visual                      # noqa: E402

from gptc import config as C                                       # noqa: E402
from gptc import design, postblocks, stimuli, task                 # noqa: E402
from gptc.recorder import Recorder, load_session1                  # noqa: E402
from gptc.widgets import ParticipantQuit, Screen, resolve_font     # noqa: E402


def ask_participant_info() -> dict:
    info = {"참가자 ID": "", "연령": "", "성별": ["여", "남", "기타/무응답"]}
    dlg = gui.DlgFromDict(
        dictionary=info, title="GPTC 세션 2", order=["참가자 ID", "연령", "성별"]
    )
    if not dlg.OK:
        core.quit()
    if not str(info["참가자 ID"]).strip():
        raise SystemExit("참가자 ID를 입력해야 합니다.")
    return info


def main() -> None:
    info = ask_participant_info()
    pid = str(info["참가자 ID"]).strip()

    recorder = Recorder(pid)
    recorder.set_meta(age=info["연령"], sex=info["성별"])

    # 참가자 ID로 시드를 고정한다. 같은 참가자를 다시 돌리면 같은 배치가 나온다.
    rng = random.Random("%s|%s" % (C.EXP_NAME, pid))

    # ── 자극 읽기 ────────────────────────────────────────────────
    sources = stimuli.load_sources()
    categories = stimuli.load_categories()
    detail_pools = stimuli.load_details()
    survey_blocks = stimuli.load_survey_items()

    # 브랜드명, 브랜드와 특징의 짝, 화면 순서, 가격을 전부 여기서 새로 뽑는다.
    all_sets = stimuli.build_candidate_sets(categories, detail_pools, rng)
    for cs in all_sets:
        for pos, cand in enumerate(cs.candidates, start=1):
            recorder.write("candidates", {
                "set_key": cs.set_key,
                "category_code": cs.category_code,
                "position": pos,
                "brand": cand.brand,
                "detail": cand.detail.text,
                "detail_type": cand.detail.detail_type,
                "price": cs.price,
            })

    # ── 창 열기 ─────────────────────────────────────────────────
    win = visual.Window(
        size=C.WIN_SIZE,
        fullscr=C.FULLSCREEN,
        color=C.BG_COLOR,
        units=C.UNITS,
        allowGUI=False,
        winType="pyglet",
    )
    win.mouseVisible = False
    font = resolve_font()
    screen = Screen(win, font)
    recorder.set_meta(font=font, frame_rate=win.getActualFrameRate())

    completed = False
    note = ""
    try:
        # ── 세션 1 자료 ──────────────────────────────────────────
        s1 = load_session1(pid)
        if s1 and s1["excluded_categories"]:
            excluded = list(s1["excluded_categories"])
            recorder.set_meta(session1_source=s1["source_file"])
        else:
            excluded = task.collect_category_interest(
                screen, categories, recorder, rng
            )
            recorder.set_meta(session1_source="in_session")

        if len(excluded) != C.N_EXCLUDED_CATEGORIES:
            raise SystemExit(
                "제외 제품군이 %d개여야 하는데 %d개입니다: %s"
                % (C.N_EXCLUDED_CATEGORIES, len(excluded), excluded)
            )
        recorder.set_meta(excluded_categories=excluded)

        main_sets = [cs for cs in all_sets if cs.category_code not in excluded]
        practice_sets = [cs for cs in all_sets if cs.category_code in excluded]

        # ── 설계 만들기 ──────────────────────────────────────────
        main_trials = design.build_main_trials(
            main_sets, sources, detail_pools, rng
        )
        practice_trials = design.build_practice_trials(
            practice_sets, detail_pools, rng, C.PRACTICE_SOURCE_LABEL
        )
        for trial in main_trials:
            recorder.write("design", trial.to_row())
        recorder.set_meta(
            n_main_trials=len(main_trials), n_practice_trials=len(practice_trials)
        )

        # ── 과제 ────────────────────────────────────────────────
        runner = task.TaskRunner(
            screen, {cs.set_key: cs for cs in all_sets}, recorder, rng
        )

        screen.instruction(C.TXT_WELCOME)
        screen.instruction(C.TXT_KEYS)
        screen.instruction(C.TXT_PRACTICE)
        runner.run_block(practice_trials)

        screen.instruction(C.TXT_TASK_START)
        runner.run_block(main_trials, break_after=len(main_trials) // 2)
        screen.instruction(C.TXT_TASK_END)

        # ── 사후 ────────────────────────────────────────────────
        # 유사도가 맨 처음이라는 점은 바꾸지 말 것. 뒤 블록이 차원을 먼저
        # 꺼내 놓으면 이 측정의 의미가 사라진다.
        postblocks.run_similarity(screen, sources, recorder, rng)

        items = survey_blocks["phase_rating"]
        decision_first = design.decision_first(pid)
        order = ("decision", "info") if decision_first else ("info", "decision")
        recorder.set_meta(phase_order="-".join(order))

        postblocks.run_phase_ratings(
            screen, order[0], sources, items, recorder, rng, block_position=1
        )
        postblocks.run_filler(screen, recorder, rng)
        postblocks.run_phase_ratings(
            screen, order[1], sources, items, recorder, rng, block_position=2
        )

        postblocks.run_processing(screen, survey_blocks["processing"], recorder, rng)

        screen.instruction(C.TXT_GOODBYE)
        completed = True

    except ParticipantQuit as exc:
        note = str(exc)
    except Exception:
        import traceback

        note = traceback.format_exc()
        raise
    finally:
        recorder.close(completed=completed, note=note)
        win.mouseVisible = True
        try:
            win.close()
        except Exception:
            pass
        core.quit()


if __name__ == "__main__":
    main()
