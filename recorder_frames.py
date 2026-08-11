# -*- coding: utf-8 -*-
"""화면 녹화. GPTC_task.py --record 로 쓴다.

프레임을 메모리에 쌓지 않고 잡는 즉시 디스크로 내보낸다. 과제 전체가 10분이
넘어서, 다 들고 있으면 몇 기가가 된다.

초당 CAPTURE_FPS장만 잡고 그것을 CAPTURE_FPS x SPEED로 재생하는 영상으로
묶는다. 그래서 결과물이 SPEED배속이 된다.
"""

from __future__ import annotations

import os
import shutil
import tempfile

from psychopy import core

CAPTURE_FPS = 5.0       # 1초에 몇 장 잡을지
SPEED = 4               # 몇 배속으로 묶을지
JPEG_QUALITY = 80


class FrameRecorder:
    def __init__(self, out_base: str, capture_fps: float = CAPTURE_FPS,
                 speed: int = SPEED):
        self.out_path = out_base if out_base.lower().endswith(".mp4") \
            else out_base + ".mp4"
        self.interval = 1.0 / capture_fps
        self.out_fps = capture_fps * speed
        self.tmp_dir = tempfile.mkdtemp(prefix="gptc_frames_")
        self.clock = core.Clock()
        self.next_at = 0.0
        self.count = 0

    def maybe_capture(self, win) -> None:
        """flip 직후에 부른다. 잡을 때가 됐으면 한 장 저장한다."""
        now = self.clock.getTime()
        if now < self.next_at:
            return
        self.next_at = now + self.interval
        try:
            win.getMovieFrame()                 # 앞 버퍼를 PIL 이미지로
            img = win.movieFrames.pop()         # 쌓이지 않게 바로 빼낸다
        except Exception:
            return
        img.convert("RGB").save(
            os.path.join(self.tmp_dir, "f%06d.jpg" % self.count),
            quality=JPEG_QUALITY,
        )
        self.count += 1

    def finish(self) -> str:
        """모아 둔 장면을 mp4로 묶고 임시 파일을 지운다."""
        if self.count == 0:
            shutil.rmtree(self.tmp_dir, ignore_errors=True)
            print("녹화된 프레임이 없습니다.")
            return ""

        import imageio.v2 as imageio

        names = sorted(os.listdir(self.tmp_dir))
        writer = imageio.get_writer(
            self.out_path, fps=self.out_fps, codec="libx264",
            quality=7, macro_block_size=None,
        )
        try:
            for name in names:
                writer.append_data(imageio.imread(os.path.join(self.tmp_dir, name)))
        finally:
            writer.close()
            shutil.rmtree(self.tmp_dir, ignore_errors=True)

        seconds = self.count / self.out_fps
        print("영상 저장: %s  (%d프레임, %.0f초, %d배속)"
              % (self.out_path, self.count, seconds, SPEED))
        return self.out_path
