# -*- coding: utf-8 -*-
"""세션 2 본 과제.

한 시행의 흐름

    고정점  ->  정보 국면 화면  ->  정보 국면 평정 1~7
            ->  고정점
            ->  결정 국면 화면  ->  산다 / 안 산다  ->  구매 의향 1~7

두 국면 모두 자극을 먼저 정해진 시간 동안 보여 주고, 그 화면을 그대로 둔 채
아래에 질문을 띄운다. 발표 자료 15·18쪽 목업과 같은 구성이다.
"""

from __future__ import annotations

import random
from typing import Dict, List, Sequence

from . import config as C
from .design import Trial
from .stimuli import CandidateSet, Category, format_price
from .widgets import BinaryChoice, LikertScale, Screen


class TaskRunner:
    def __init__(
        self,
        screen: Screen,
        sets_by_key: Dict[str, CandidateSet],
        recorder,
        rng: random.Random,
    ):
        self.screen = screen
        self.sets = sets_by_key
        self.recorder = recorder
        self.rng = rng
        self.scale = LikertScale(screen)
        self.binary = BinaryChoice(screen, C.OPT_BUY, C.OPT_NOBUY)

    # ------------------------------------------------------------------
    #  화면 조각
    # ------------------------------------------------------------------

    def _header(self, trial: Trial) -> List:
        """맨 위 정보원 라벨과 그 아래 제품군 이름.

        여섯 정보원의 화면 문구는 글자 그대로 같다. 바뀌는 것은 이 라벨뿐이라,
        노란색으로 크게 띄워 어느 정보원인지 놓치지 않게 한다.
        """
        return [
            self.screen.text(
                trial.source_label,
                pos=(0, C.Y_SOURCE_LABEL),
                height=C.H_SOURCE_LABEL,
                color=C.SOURCE_LABEL_COLOR,
                bold=True,
            ),
            self.screen.text(
                trial.category_kr,
                pos=(0, C.Y_CATEGORY),
                height=C.H_CATEGORY,
                color=C.DIM_COLOR,
            ),
        ]

    def _info_stims(self, trial: Trial) -> List:
        stims = self._header(trial)
        for i, (brand, detail) in enumerate(
            zip(trial.candidate_brands, trial.candidate_details)
        ):
            stims.append(
                self.screen.text(
                    "%s  -  %s" % (brand, detail),
                    pos=(0, C.Y_CANDIDATES_TOP - i * C.CANDIDATE_GAP),
                    height=C.H_FEATURE,
                    wrap=1.3,
                )
            )
        return stims

    def _decision_stims(self, trial: Trial) -> List:
        stims = self._header(trial)
        stims.append(
            self.screen.text(
                trial.rec_brand, pos=(0, C.Y_BRAND), height=C.H_BRAND, bold=True
            )
        )
        stims.append(
            self.screen.text(
                format_price(trial.price),
                pos=(0, C.Y_PRICE),
                height=C.H_PRICE,
                bold=True,
            )
        )
        # 정보 국면에서 달고 있던 특징이 맨 위에 오고, 그 아래로 나머지가 붙는다
        for i, line in enumerate([trial.rec_detail] + trial.extra_lines):
            stims.append(
                self.screen.text(
                    "· " + line,
                    pos=(0, C.Y_DETAIL_TOP - i * C.DETAIL_GAP),
                    height=C.H_DETAIL,
                    color=C.DIM_COLOR,
                    wrap=1.3,
                )
            )
        return stims

    # ------------------------------------------------------------------
    #  한 시행
    # ------------------------------------------------------------------

    def run_trial(self, trial: Trial) -> dict:
        row = trial.to_row()

        # 1. 정보 국면 -------------------------------------------------
        # 글자 만드는 비용을 고정점 구간 안으로 넣는다. 고정점이 끝나자마자
        # 자극이 떠야 하는데, 여기서 만들면 그만큼 제시가 늦어진다.
        info_stims = self._info_stims(trial)
        row["fix1_dur"] = round(self.screen.fixation(self.rng), 3)
        self.screen.hold(info_stims, C.INFO_VIEW_DUR)
        info_score, info_rt = self.scale.collect(
            C.Q_INFO_PHASE, C.Q_INFO_LEFT, C.Q_INFO_RIGHT, context=info_stims
        )
        row["info_accept"] = info_score if info_score is not None else ""
        row["info_accept_rt"] = round(info_rt, 4) if info_rt is not None else ""

        # 2. 결정 국면 -------------------------------------------------
        dec_stims = self._decision_stims(trial)
        row["fix2_dur"] = round(self.screen.fixation(self.rng), 3)
        self.screen.hold(dec_stims, C.DECISION_VIEW_DUR)

        choice, choice_rt = self.binary.collect(C.Q_DECISION_BINARY, context=dec_stims)
        row["purchase_choice"] = choice if choice is not None else ""
        row["purchase_choice_bin"] = "" if choice is None else int(choice == C.OPT_BUY)
        row["purchase_choice_rt"] = round(choice_rt, 4) if choice_rt is not None else ""

        intent, intent_rt = self.scale.collect(
            C.Q_DECISION_SCALE, C.Q_DECISION_LEFT, C.Q_DECISION_RIGHT, context=dec_stims
        )
        row["purchase_intent"] = intent if intent is not None else ""
        row["purchase_intent_rt"] = round(intent_rt, 4) if intent_rt is not None else ""

        self.recorder.write("task", row)
        return row

    # ------------------------------------------------------------------
    #  블록
    # ------------------------------------------------------------------

    def run_block(self, trials: Sequence[Trial], break_after: int = None) -> None:
        for i, trial in enumerate(trials, start=1):
            self.run_trial(trial)
            if break_after and i == break_after and i < len(trials):
                self.screen.instruction(C.TXT_BREAK)


# ─────────────────────────────────────────────
#  제품군 관심도
# ─────────────────────────────────────────────


def collect_category_interest(
    screen: Screen,
    categories: Dict[str, Category],
    recorder,
    rng: random.Random,
    n_exclude: int = None,
) -> List[str]:
    """제품군마다 일반적인 관심도를 받고 가장 낮은 몇 개를 뺀다.

    재는 것은 그 종류 전반에 대한 관심이다. 특정 제품에 대한 선호를 묻지
    않는다. 관심 없는 제품군이 섞이면 "살 만한 게 있어 보입니까"가 정보원과
    무관하게 바닥에 깔려서 과제가 죽는다.

    원래는 세션 1에서 한다. 세션 1 자료가 없을 때만 여기서 받는다.
    """
    n_exclude = C.N_EXCLUDED_CATEGORIES if n_exclude is None else n_exclude
    screen.instruction(C.TXT_INTEREST_BLOCK)
    scale = LikertScale(screen)

    order = list(categories.values())
    rng.shuffle(order)
    scores: Dict[str, int] = {}

    for position, cat in enumerate(order, start=1):
        context = [
            screen.text(
                cat.category_kr,
                pos=(0, 0.20),
                height=C.H_SOURCE_LABEL,
                color=C.SOURCE_LABEL_COLOR,
                bold=True,
            )
        ]
        score, rt = scale.collect(
            C.Q_INTEREST,
            C.Q_INTEREST_LEFT,
            C.Q_INTEREST_RIGHT,
            context=context,
            timeout=C.SURVEY_TIMEOUT,
        )
        scores[cat.category_code] = 0 if score is None else score
        recorder.write(
            "category_interest",
            {
                "position": position,
                "category_code": cat.category_code,
                "category_kr": cat.category_kr,
                "interest": score if score is not None else "",
                "rt": round(rt, 4) if rt is not None else "",
                "source": "in_session",
            },
        )
        screen.blank(C.SURVEY_ITEM_GAP)

    # 점수가 낮은 순, 같으면 무작위로 갈라 뺀다
    ranked = sorted(scores, key=lambda code: (scores[code], rng.random()))
    return ranked[:n_exclude]
