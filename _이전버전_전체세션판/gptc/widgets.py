# -*- coding: utf-8 -*-
"""PsychoPy 화면 요소와 응답 수집.

여기부터 psychopy를 쓴다. 화면을 그리고, 키를 받고, 반응시간을 잰다.
"""

from __future__ import annotations

import random
from typing import List, Optional, Sequence, Tuple

from psychopy import core, event, visual

from . import config as C


class ParticipantQuit(Exception):
    """참가자나 실험자가 도중에 끝냈을 때."""


# ─────────────────────────────────────────────
#  폰트
# ─────────────────────────────────────────────


def resolve_font() -> str:
    """설치된 폰트 중 한글이 나오는 첫 후보를 고른다."""
    try:
        from psychopy.visual.textbox2.fontmanager import FontManager

        available = set(FontManager().getFontFamilyNames())
        for cand in C.FONT_CANDIDATES:
            if cand in available:
                return cand
    except Exception:
        pass
    return C.FONT_CANDIDATES[0]


# ─────────────────────────────────────────────
#  화면
# ─────────────────────────────────────────────


class Screen:
    """창 하나와 거기 얹는 글자들을 함께 관리한다."""

    def __init__(self, win: visual.Window, font: str):
        self.win = win
        self.font = font
        # 매 시행 다시 만들면 그만큼 제시가 늦어진다. 한 번 만들어 두고 쓴다.
        self._pause_stim = self.text(
            C.TXT_PAUSED, pos=(0, 0), height=C.H_INSTRUCTION, color=C.WARN_COLOR
        )
        self._fix_stim = self.text("+", height=0.07)

    # 만들기 ------------------------------------------------------------

    def text(
        self,
        message: str = "",
        pos: Tuple[float, float] = (0, 0),
        height: float = C.H_FEATURE,
        color: str = C.TEXT_COLOR,
        wrap: float = 1.4,
        bold: bool = False,
    ):
        """가운데 정렬 글자 하나.

        TextStim이 아니라 TextBox2를 쓴다. TextStim은 pyglet의 win32 폰트
        경로를 타는데, PsychoPy가 윈도우에서 고정해 둔 pyglet 1.4.11이
        Python 3.12에서 깨진다(_create_bitmap의 ctypes 인자 타입 오류).
        TextBox2는 freetype으로 직접 그려서 그 경로를 안 탄다. 한글도 이쪽이
        낫다.
        """
        return visual.TextBox2(
            self.win,
            text=message,
            pos=pos,
            letterHeight=height,
            color=color,
            font=self.font,
            bold=bold,
            alignment="center",
            anchor="center",
            size=(wrap, None),
            units=C.UNITS,
            editable=False,
        )

    # 그리기 ------------------------------------------------------------

    def draw(self, stims: Sequence) -> None:
        for s in stims:
            s.draw()

    def flip(self) -> float:
        return self.win.flip()

    def blank(self, duration: float) -> None:
        self.win.flip()
        core.wait(duration)

    def fixation(self, rng: random.Random) -> float:
        """지터가 들어간 고정점. 실제로 머문 시간을 돌려준다."""
        dur = rng.uniform(C.FIX_MIN, C.FIX_MAX)
        clock = core.Clock()
        while clock.getTime() < dur:
            self._fix_stim.draw()
            self.win.flip()
            self._check_quit()
        return dur

    # 키 --------------------------------------------------------------

    def pause(self) -> None:
        """일시 정지 화면. Y면 종료, N이면 하던 데로 돌아간다."""
        event.clearEvents()
        while True:
            self._pause_stim.draw()
            self.win.flip()
            for key in event.getKeys(keyList=["y", "n"]):
                if key == "y":
                    raise ParticipantQuit("실험자 종료")
                event.clearEvents()
                return

    def _check_quit(self) -> None:
        """escape가 눌렸으면 일시 정지 화면을 띄운다."""
        if event.getKeys(keyList=[C.KEY_QUIT]):
            self.pause()

    def wait_for_space(self, stims: Sequence) -> None:
        event.clearEvents()
        while True:
            self.draw(stims)
            self.win.flip()
            keys = event.getKeys(keyList=[C.KEY_ADVANCE, C.KEY_QUIT])
            if C.KEY_QUIT in keys:
                self.pause()
            elif C.KEY_ADVANCE in keys:
                return

    def instruction(self, body: str) -> None:
        """안내 화면. 스페이스바를 누를 때까지 머문다."""
        stim = self.text(body, pos=(0, 0.02), height=C.H_INSTRUCTION, wrap=1.5)
        self.wait_for_space([stim])

    def hold(self, stims: Sequence, duration: float) -> None:
        """정해진 시간 동안 화면을 유지한다."""
        clock = core.Clock()
        while clock.getTime() < duration:
            self.draw(stims)
            self.win.flip()
            self._check_quit()


# ─────────────────────────────────────────────
#  리커트 7점
# ─────────────────────────────────────────────


class LikertScale:
    """원 7개를 좌우 키로 옮기고 Enter로 확정한다.

    첫 입력은 방향과 무관하게 가운데(4)에서 시작한다. 기존 PsychoJS 코드와
    같은 동작이다. 어느 쪽 끝에서 출발하느냐가 응답을 밀지 않게 하려는 것.
    """

    def __init__(self, screen: Screen, n: int = None):
        self.screen = screen
        self.n = n or C.SCALE_N
        step = (
            (C.SCALE_X_RIGHT - C.SCALE_X_LEFT) / (self.n - 1) if self.n > 1 else 0.0
        )
        self.xs = [C.SCALE_X_LEFT + i * step for i in range(self.n)]

        self.circles = [
            visual.Circle(
                screen.win,
                radius=C.CIRCLE_RADIUS,
                edges=64,
                lineColor=C.TEXT_COLOR,
                lineWidth=C.CIRCLE_LINE_WIDTH,
                fillColor=None,
                pos=(x, C.Y_SCALE),
                units=C.UNITS,
            )
            for x in self.xs
        ]
        self.numbers = [
            screen.text(str(i + 1), pos=(x, C.Y_SCALE_NUM), height=C.H_SCALE_NUM)
            for i, x in enumerate(self.xs)
        ]
        self.left_anchor = screen.text(
            "", pos=(C.SCALE_X_LEFT, C.Y_ANCHOR), height=C.H_ANCHOR, wrap=0.5
        )
        self.right_anchor = screen.text(
            "", pos=(C.SCALE_X_RIGHT, C.Y_ANCHOR), height=C.H_ANCHOR, wrap=0.5
        )
        self.question = screen.text(
            "", pos=(0, C.Y_QUESTION), height=C.H_QUESTION, wrap=1.5
        )

    def _paint(self, selected: Optional[int]) -> None:
        for i, circ in enumerate(self.circles):
            circ.fillColor = C.ACCENT_COLOR if i == selected else None

    def collect(
        self,
        question: str,
        left: str,
        right: str,
        context: Sequence = (),
        timeout: float = None,
    ) -> Tuple[Optional[int], Optional[float]]:
        """점수(1~7)와 반응시간을 돌려준다. 시간이 다 되면 (None, None)."""
        timeout = C.RESPONSE_TIMEOUT if timeout is None else timeout
        self.question.text = question
        self.left_anchor.text = left
        self.right_anchor.text = right

        selected: Optional[int] = None
        mid = self.n // 2
        event.clearEvents()
        clock = core.Clock()

        while clock.getTime() < timeout:
            for key in event.getKeys(
                keyList=[C.KEY_LEFT, C.KEY_RIGHT, C.KEY_CONFIRM, C.KEY_QUIT]
            ):
                if key == C.KEY_QUIT:
                    self.screen.pause()
                elif key == C.KEY_LEFT:
                    selected = mid if selected is None else max(0, selected - 1)
                elif key == C.KEY_RIGHT:
                    selected = mid if selected is None else min(self.n - 1, selected + 1)
                elif key == C.KEY_CONFIRM and selected is not None:
                    rt = clock.getTime()
                    self._paint(selected)
                    self.screen.hold(self._all(context), C.FEEDBACK_FLASH)
                    return selected + 1, rt

            self._paint(selected)
            self.screen.draw(self._all(context))
            self.screen.win.flip()

        return None, None

    def _all(self, context: Sequence) -> List:
        return (
            list(context)
            + [self.question, self.left_anchor, self.right_anchor]
            + self.circles
            + self.numbers
        )


# ─────────────────────────────────────────────
#  이분 선택 (산다 / 안 산다)
# ─────────────────────────────────────────────


class BinaryChoice:
    """좌우 두 칸 중 하나를 고른다. 선택된 칸에 테두리가 생긴다."""

    def __init__(self, screen: Screen, left_text: str, right_text: str):
        self.screen = screen
        self.options = (left_text, right_text)
        self.labels = [
            screen.text(
                left_text, pos=(-C.BINARY_X, C.Y_BINARY), height=C.H_QUESTION, bold=True
            ),
            screen.text(
                right_text, pos=(C.BINARY_X, C.Y_BINARY), height=C.H_QUESTION, bold=True
            ),
        ]
        self.boxes = [
            visual.Rect(
                screen.win,
                width=C.BINARY_BOX_W,
                height=C.BINARY_BOX_H,
                pos=(-C.BINARY_X, C.Y_BINARY),
                lineColor=C.ACCENT_COLOR,
                lineWidth=C.CIRCLE_LINE_WIDTH,
                fillColor=None,
                units=C.UNITS,
            ),
            visual.Rect(
                screen.win,
                width=C.BINARY_BOX_W,
                height=C.BINARY_BOX_H,
                pos=(C.BINARY_X, C.Y_BINARY),
                lineColor=C.ACCENT_COLOR,
                lineWidth=C.CIRCLE_LINE_WIDTH,
                fillColor=None,
                units=C.UNITS,
            ),
        ]
        self.prompt = screen.text(
            "", pos=(0, C.Y_QUESTION), height=C.H_QUESTION, wrap=1.5
        )

    def collect(
        self, prompt: str, context: Sequence = (), timeout: float = None
    ) -> Tuple[Optional[str], Optional[float]]:
        """고른 문구와 반응시간. 시간이 다 되면 (None, None)."""
        timeout = C.RESPONSE_TIMEOUT if timeout is None else timeout
        self.prompt.text = prompt
        selected: Optional[int] = None
        event.clearEvents()
        clock = core.Clock()

        while clock.getTime() < timeout:
            for key in event.getKeys(
                keyList=[C.KEY_LEFT, C.KEY_RIGHT, C.KEY_CONFIRM, C.KEY_QUIT]
            ):
                if key == C.KEY_QUIT:
                    self.screen.pause()
                elif key == C.KEY_LEFT:
                    selected = 0
                elif key == C.KEY_RIGHT:
                    selected = 1
                elif key == C.KEY_CONFIRM and selected is not None:
                    rt = clock.getTime()
                    self.screen.hold(self._all(context, selected), C.FEEDBACK_FLASH)
                    return self.options[selected], rt

            self.screen.draw(self._all(context, selected))
            self.screen.win.flip()

        return None, None

    def _all(self, context: Sequence, selected: Optional[int]) -> List:
        stims = list(context) + [self.prompt] + self.labels
        if selected is not None:
            stims.append(self.boxes[selected])
        return stims


# ─────────────────────────────────────────────
#  여러 보기 중 하나 고르기 (조작 점검용)
# ─────────────────────────────────────────────


class MultipleChoice:
    """보기를 세로로 늘어놓고 위아래 키로 고른다."""

    def __init__(self, screen: Screen, top: float = 0.10, gap: float = 0.085):
        self.screen = screen
        self.top = top
        self.gap = gap
        self.prompt = screen.text("", pos=(0, 0.30), height=C.H_QUESTION, wrap=1.6)

    def collect(
        self, prompt: str, options: Sequence[str], timeout: float = None
    ) -> Tuple[Optional[int], Optional[float]]:
        """고른 보기의 인덱스(0부터)와 반응시간."""
        timeout = C.SURVEY_TIMEOUT if timeout is None else timeout
        self.prompt.text = prompt
        stims = [
            self.screen.text(
                "%d.  %s" % (i + 1, opt),
                pos=(0, self.top - i * self.gap),
                height=C.H_DETAIL,
                wrap=1.5,
            )
            for i, opt in enumerate(options)
        ]

        selected: Optional[int] = None
        event.clearEvents()
        clock = core.Clock()

        while clock.getTime() < timeout:
            for key in event.getKeys(
                keyList=["up", "down", C.KEY_CONFIRM, C.KEY_QUIT]
            ):
                if key == C.KEY_QUIT:
                    self.screen.pause()
                elif key == "down":
                    selected = 0 if selected is None else min(len(options) - 1, selected + 1)
                elif key == "up":
                    selected = 0 if selected is None else max(0, selected - 1)
                elif key == C.KEY_CONFIRM and selected is not None:
                    return selected, clock.getTime()

            for i, stim in enumerate(stims):
                stim.color = C.ACCENT_COLOR if i == selected else C.TEXT_COLOR
            self.prompt.draw()
            self.screen.draw(stims)
            self.screen.win.flip()

        return None, None
