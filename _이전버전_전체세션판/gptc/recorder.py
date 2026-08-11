# -*- coding: utf-8 -*-
"""데이터 저장.

블록마다 긴 형식(long format) CSV를 하나씩 쓴다. 한 행이 하나의 응답이다.
행을 쓸 때마다 디스크로 밀어내기 때문에 중간에 꺼져도 그때까지는 남는다.
"""

from __future__ import annotations

import csv
import io
import json
import os
from datetime import datetime
from typing import Dict, List, Optional

from . import config as C


class Recorder:
    def __init__(self, participant_id: str, data_dir: str = None):
        self.participant_id = str(participant_id).strip() or "NA"
        self.data_dir = data_dir or C.DATA_DIR
        os.makedirs(self.data_dir, exist_ok=True)
        self.started = datetime.now()
        self.stamp = self.started.strftime("%Y-%m-%d_%Hh%M.%S")
        self._files: Dict[str, io.TextIOBase] = {}
        self._writers: Dict[str, csv.DictWriter] = {}
        self.meta: Dict[str, object] = {
            "participant_id": self.participant_id,
            "experiment": C.EXP_NAME,
            "started": self.started.isoformat(timespec="seconds"),
        }

    # ------------------------------------------------------------------

    def write(self, block: str, row: dict) -> None:
        """한 행 저장. 첫 호출 때 그 행의 키로 열 이름을 잡는다."""
        full = {
            "participant_id": self.participant_id,
            "timestamp": datetime.now().isoformat(timespec="milliseconds"),
        }
        full.update(row)

        if block not in self._writers:
            path = os.path.join(
                self.data_dir,
                "%s_%s_%s_%s.csv"
                % (self.participant_id, C.EXP_NAME, block, self.stamp),
            )
            fh = io.open(path, "w", encoding="utf-8-sig", newline="")
            writer = csv.DictWriter(
                fh, fieldnames=list(full), restval="", extrasaction="ignore"
            )
            writer.writeheader()
            self._files[block] = fh
            self._writers[block] = writer

        self._writers[block].writerow(full)
        self._files[block].flush()

    # ------------------------------------------------------------------

    def set_meta(self, **kwargs) -> None:
        self.meta.update(kwargs)

    def close(self, completed: bool = True, note: str = "") -> None:
        self.meta["completed"] = bool(completed)
        self.meta["ended"] = datetime.now().isoformat(timespec="seconds")
        self.meta["duration_min"] = round(
            (datetime.now() - self.started).total_seconds() / 60.0, 2
        )
        if note:
            self.meta["note"] = note

        path = os.path.join(
            self.data_dir,
            "%s_%s_meta_%s.json" % (self.participant_id, C.EXP_NAME, self.stamp),
        )
        with io.open(path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(self.meta, ensure_ascii=False, indent=2))

        for fh in self._files.values():
            try:
                fh.close()
            except Exception:
                pass
        self._files.clear()
        self._writers.clear()


# ─────────────────────────────────────────────
#  세션 1 입력 읽기
# ─────────────────────────────────────────────


def load_session1(participant_id: str, folder: str = None) -> Optional[dict]:
    """세션 1 결과를 읽는다. 없으면 None.

    기대하는 파일: session1_input/<참가자ID>.csv
    한 행이 하나의 항목인 긴 형식이다.

      excluded,bt_speaker      <- 관심도가 낮아 빼는 제품군
      interest,keyboard,5      <- 제품군별 관심도 (기록용, 선택)

    삼종 순위는 받지 않는다. 재는 것은 제품군 전반에 대한 관심이다.
    """
    folder = folder or C.SESSION1_DIR
    path = os.path.join(folder, "%s.csv" % str(participant_id).strip())
    if not os.path.exists(path):
        return None

    excluded: List[str] = []
    interest: Dict[str, int] = {}
    with io.open(path, encoding="utf-8-sig", newline="") as fh:
        for raw in csv.reader(fh):
            row = [c.strip() for c in raw if c is not None]
            if not row or not row[0] or row[0].startswith("#"):
                continue
            kind = row[0].lower()
            if kind in ("excluded", "exclude"):
                excluded.append(row[1])
            elif kind == "interest" and len(row) >= 3:
                interest[row[1]] = int(row[2])

    return {"excluded_categories": excluded, "interest": interest, "source_file": path}
