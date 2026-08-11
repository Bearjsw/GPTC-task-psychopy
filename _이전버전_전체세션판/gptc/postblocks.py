# -*- coding: utf-8 -*-
"""세션 2 사후 블록.

순서 (GPTC_행동실험_Ko.pdf 4·7쪽)

    유사도 15쌍  ->  국면 A 평정  ->  간섭 과제  ->  국면 B 평정  ->  처리 동기

유사도는 반드시 맨 처음에 온다. 뒤 블록이 능력·정직성 같은 차원을 먼저 꺼내
놓으면 유사도 판단이 그 차원을 따라가 버리고, 그 값으로 RQ4를 검정하면
순환논증이 된다.

국면 A와 B 중 어느 쪽을 먼저 답할지는 참가자 절반씩 갈린다.
"""

from __future__ import annotations

import random
from typing import Sequence

from psychopy import core, event

from . import config as C
from .design import phase_rating_order, similarity_order
from .stimuli import Source, SurveyItem
from .widgets import LikertScale, Screen


# ─────────────────────────────────────────────
#  ① 유사도 15쌍
# ─────────────────────────────────────────────


def run_similarity(
    screen: Screen, sources: Sequence[Source], recorder, rng: random.Random
) -> None:
    screen.instruction(C.TXT_SIMILARITY)
    scale = LikertScale(screen)

    for position, (a, b) in enumerate(similarity_order(sources, rng), start=1):
        context = [
            screen.text(a.short_name, pos=(-0.30, 0.17), height=C.H_SOURCE_LABEL,
                        color=C.SOURCE_LABEL_COLOR, bold=True, wrap=0.55),
            screen.text("-", pos=(0, 0.17), height=C.H_SOURCE_LABEL, color=C.DIM_COLOR),
            screen.text(b.short_name, pos=(0.30, 0.17), height=C.H_SOURCE_LABEL,
                        color=C.SOURCE_LABEL_COLOR, bold=True, wrap=0.55),
        ]
        score, rt = scale.collect(
            C.Q_SIMILARITY,
            C.Q_SIM_LEFT,
            C.Q_SIM_RIGHT,
            context=context,
            timeout=C.SURVEY_TIMEOUT,
        )
        recorder.write(
            "similarity",
            {
                "position": position,
                "source_a": a.source_code,
                "source_b": b.source_code,
                "pair_key": "_".join(sorted((a.source_code, b.source_code))),
                "similarity": score if score is not None else "",
                "rt": round(rt, 4) if rt is not None else "",
            },
        )
        screen.blank(C.SURVEY_ITEM_GAP)


# ─────────────────────────────────────────────
#  ② 국면별 평정
# ─────────────────────────────────────────────


def run_phase_ratings(
    screen: Screen,
    phase: str,
    sources: Sequence[Source],
    items: Sequence[SurveyItem],
    recorder,
    rng: random.Random,
    block_position: int,
) -> None:
    """phase는 'info' 또는 'decision'.

    두 국면에서 묻는 문항은 완전히 같다. 앞에 붙는 회상 프레임 한 문장만
    다르다. 그래서 안내 화면만 갈아 끼우고 문항은 그대로 쓴다.
    """
    screen.instruction(C.TXT_PHASE_INFO if phase == "info" else C.TXT_PHASE_DECISION)
    scale = LikertScale(screen)

    for position, (source, item) in enumerate(
        phase_rating_order(sources, items, rng), start=1
    ):
        name = source.short_name
        context = [
            screen.text(source.label, pos=(0, 0.22), height=C.H_SOURCE_LABEL,
                        color=C.SOURCE_LABEL_COLOR, bold=True)
        ]
        score, rt = scale.collect(
            item.rendered(name),
            item.left_anchor,
            item.right_anchor,
            context=context,
            timeout=C.SURVEY_TIMEOUT,
        )
        recorder.write(
            "phase_ratings",
            {
                "phase": phase,
                "block_position": block_position,     # 1이면 먼저 답한 국면
                "position": position,
                "source_code": source.source_code,
                "item_id": item.item_id,
                "dimension": item.dimension,
                "score": score if score is not None else "",
                "rt": round(rt, 4) if rt is not None else "",
            },
        )
        screen.blank(C.SURVEY_ITEM_GAP)


# ─────────────────────────────────────────────
#  ③ 처리 동기
# ─────────────────────────────────────────────


def run_processing(
    screen: Screen, items: Sequence[SurveyItem], recorder, rng: random.Random
) -> None:
    screen.instruction(C.TXT_PROCESSING)
    scale = LikertScale(screen)
    order = list(items)
    rng.shuffle(order)

    for position, item in enumerate(order, start=1):
        score, rt = scale.collect(
            item.text,
            item.left_anchor,
            item.right_anchor,
            timeout=C.SURVEY_TIMEOUT,
        )
        recorder.write(
            "processing",
            {
                "position": position,
                "item_id": item.item_id,
                "dimension": item.dimension,
                "score": score if score is not None else "",
                "rt": round(rt, 4) if rt is not None else "",
            },
        )
        screen.blank(C.SURVEY_ITEM_GAP)


# ─────────────────────────────────────────────
#  ④ 간섭 과제
# ─────────────────────────────────────────────


def run_filler(screen: Screen, recorder, rng: random.Random) -> None:
    """두 국면 평정 사이에 끼우는 짧은 계산 과제.

    한 자릿수 덧셈과 뺄셈만 낸다. 어려울 필요가 없다. 앞 블록에 적은 답을
    그대로 옮겨 적는 흐름을 끊어 주면 된다.
    """
    screen.instruction(C.TXT_FILLER)

    for index in range(1, C.N_FILLER_TRIALS + 1):
        if rng.random() < 0.5:
            a, b = rng.randint(2, 9), rng.randint(1, 8)
            op, answer = "+", a + b
        else:
            a = rng.randint(3, 9)
            b = rng.randint(1, a - 1)               # 음수가 안 나오게
            op, answer = "-", a - b

        truthful = rng.random() < 0.5
        shown = answer if truthful else answer + rng.choice((-2, -1, 1, 2))

        stim = screen.text(
            "%d  %s  %d  =  %d" % (a, op, b, shown),
            pos=(0, 0.06),
            height=0.09,
            bold=True,
        )
        hint = screen.text(
            "맞으면  ←        틀리면  →",
            pos=(0, -0.16),
            height=C.H_ANCHOR,
            color=C.DIM_COLOR,
        )

        event.clearEvents()
        clock = core.Clock()
        said_true = None
        while said_true is None and clock.getTime() < C.SURVEY_TIMEOUT:
            screen.draw([stim, hint])
            screen.win.flip()
            for key in event.getKeys(keyList=[C.KEY_LEFT, C.KEY_RIGHT, C.KEY_QUIT]):
                if key == C.KEY_QUIT:
                    screen.pause()
                else:
                    said_true = key == C.KEY_LEFT

        rt = clock.getTime()
        hit = None if said_true is None else said_true == truthful
        if hit is not None:
            screen.hold(
                [stim, screen.text("O" if hit else "X", pos=(0, -0.16), height=0.07,
                                   color="lime" if hit else C.ACCENT_COLOR)],
                C.FILLER_FEEDBACK,
            )

        recorder.write(
            "filler",
            {
                "index": index,
                "problem": "%d %s %d" % (a, op, b),
                "shown_answer": shown,
                "is_true_equation": int(truthful),
                "responded_true": "" if said_true is None else int(said_true),
                "hit": "" if hit is None else int(hit),
                "rt": round(rt, 4),
            },
        )
        screen.blank(C.SURVEY_ITEM_GAP)
