# -*- coding: utf-8 -*-
"""GPTC 행동 선행실험 · 본 과제 · 0818 제품 리스트판 (PsychoPy)

GPTC_task.py 와 같은 과제인데 자극이 다르다. 이쪽은 0818_product_list.xlsx 를
옮긴 stim_0818/ 을 읽는다. 제품군이 8개에서 21개로 늘고 대분류 7개가 붙었으며,
결정 국면에 세 줄 대신 요약 문장 한 줄이 나온다. 빼는 제품군은 없다.

    제품군 21 x 반복 2 = 42시행,  정보원 6종당 7시행
    연습은 본 과제에 안 나오는 바람막이로 4시행

사전·사후 설문은 구글 설문으로 받는다. 이 파일은 과제만 돌린다.
문항은 구글설문_문항/ 아래 문서로 빼 두었다.

Rowen이 쓴 experiment.js의 구성을 따랐다. 맨 위 CFG에 상수를 모으고, 자극을
정해진 시간 동안 띄운 뒤 지터가 들어간 고정점으로 끊고, 리커트는 원 7개를 좌우
키로 옮겨 Enter로 확정한다. 시행 하나가 CSV 한 행이고 구간별 시각을 열로 남긴다.

실행
    python GPTC_task_0818.py                실제 진행
    python GPTC_task_0818.py --windowed     창 모드 (화면 확인용)
    python GPTC_task_0818.py --autopilot    가상 참가자가 자동으로 응답
    python GPTC_task_0818.py --record out   화면을 녹화해서 out.mp4 로 저장
"""

from __future__ import annotations

import os
import sys

# 한국어 윈도우에서 psychopy.gui가 import 단계에서 죽는 것을 막는다.
# i18next가 한국어 번역 JSON을 열 때 인코딩을 지정하지 않아 시스템 기본값
# (cp949)으로 읽다가 UnicodeDecodeError를 낸다. UTF-8 모드로 다시 띄운다.
# os.execv는 쓰지 않는다. 윈도우에서는 자식의 출력과 종료 코드가 사라진다.
if not sys.flags.utf8_mode:
    import subprocess

    sys.exit(subprocess.call([sys.executable, "-X", "utf8"] + sys.argv))

import csv
import io
import json
import random
import re
from datetime import datetime

from psychopy import core, data, event, gui, visual


# ─────────────────────────────────────────────
#  CFG
# ─────────────────────────────────────────────

CFG = {
    # 시행 타이밍 (초)
    "info_dur":             7.5,    # 정보 국면 자극을 띄워 두는 시간
    "decision_dur":         6.0,    # 결정 국면 자극을 띄워 두는 시간
    "fix_min":              0.5,    # 고정점 지터 범위
    "fix_max":              1.5,
    "response_timeout":    12.0,    # 무응답 상한. 넘기면 결측으로 남기고 넘어간다
    "feedback_flash":       0.25,   # 확정 뒤 선택 표시를 남겨 두는 시간
    "intro_fix_dur":        2.0,    # 과제 시작 직전 고정점

    # 설계
    "sets_per_category":    1,      # 제품군 21개를 전부 쓰므로 제품군당 한 세트
    "candidates_per_set":   3,      # 정보 국면에 늘어놓는 후보 수
    "repeats_per_set":      2,      # 같은 세트를 몇 번 보여 줄지 (정보원만 바뀜)
    "n_practice":           4,      # 첫 시행 적응이 안 된다는 보고가 있어 2에서 늘렸다
    "price_step":           1000,

    # 무작위화 제약
    "max_run":              2,      # 같은 정보원 / 같은 제품군 최대 연속 횟수
    "max_run_major":        2,      # 같은 대분류 최대 연속 횟수
    "min_repeat_lag":       6,      # 같은 세트가 다시 나오기까지 최소 간격

    # 색
    "bg_color":            "black",
    "text_color":          "white",
    "dim_color":           "#9aa0a6",
    "label_color":         "yellow",   # 정보원 라벨. 본문과 확실히 갈라 놓는다
    "accent_color":        "red",      # 선택된 리커트 원
    "warn_color":          "yellow",

    # 글자
    "font_candidates": ["NanumGothic", "Malgun Gothic", "Noto Sans KR", "Arial"],
    "text_bold":            True,
    "h_label":              0.085,  # 정보원 라벨
    "h_category":           0.042,
    "h_brand":              0.046,
    "h_feature":            0.038,
    "h_price":              0.050,
    "h_detail":             0.034,
    "h_question":           0.042,
    "h_number":             0.034,
    "h_anchor":             0.028,
    "h_instruction":        0.038,

    # 화면 배치
    "label_y":              0.40,
    "category_y":           0.33,
    "candidates_top":       0.24,
    "candidate_gap":        0.10,
    "brand_y":              0.25,
    "price_y":              0.17,
    "detail_top":           0.06,
    "detail_gap":           0.055,

    # 리커트 7점
    "scale_n":              7,
    "circle_radius":        0.038,
    "circle_line_width":    3.0,
    "question_y":          -0.15,
    "scale_y":             -0.26,
    "numbers_y":           -0.335,
    "desc_y":              -0.395,
    "scale_x_left":        -0.36,
    "scale_x_right":        0.36,

    # 이분 선택
    "binary_x":             0.27,
    "binary_y":            -0.26,
    "binary_box_w":         0.40,
    "binary_box_h":         0.10,

    # 키
    "key_left":            "left",
    "key_right":           "right",
    "key_confirm":         "return",
    "key_advance":         "space",
    "key_quit":            "escape",
}

EXP_NAME = "GPTC_task_0818"
ROOT = os.path.dirname(os.path.abspath(__file__))
STIM_DIR = os.path.join(ROOT, "stim_0818")
DATA_DIR = os.path.join(ROOT, "data")


# ─────────────────────────────────────────────
#  문항
# ─────────────────────────────────────────────

Q_INFO = "이 중에 구매할 만한 게 있어 보입니까?"
Q_INFO_LEFT, Q_INFO_RIGHT = "전혀 없어 보인다", "매우 있어 보인다"

Q_BINARY = "이 제품을 구매하시겠습니까?"
OPT_BUY, OPT_NOBUY = "구매한다", "구매하지 않는다"

Q_INTENT = "얼마나 구매하고 싶습니까?"
Q_INTENT_LEFT, Q_INTENT_RIGHT = "전혀 구매하고 싶지 않다", "매우 구매하고 싶다"

PRACTICE_LABEL = "[예시 정보원]"

TXT_WELCOME = """이제 과제를 시작합니다.

화면에는 여섯 정보원 가운데 하나가 제품을 골라 알려 줍니다.
설문에서 읽으신 정보원들입니다. 저마다 고르는 방식이 다릅니다.

한 시행은 두 단계로 이어집니다.

  1단계   정보원이 후보 세 개를 걸러서 보여 줍니다.
  2단계   그중 하나를 가격과 함께 추천합니다.

계속하려면 스페이스바를 누르세요."""

TXT_KEYS = """응답 방법

  ←  →      선택을 옮깁니다
  Enter     선택을 확정합니다

한 번 확정하면 되돌릴 수 없습니다.
확정하기 전에 화면을 확인해 주세요.

계속하려면 스페이스바를 누르세요."""

TXT_PRACTICE = """먼저 연습을 네 번 하겠습니다.

연습에 나오는 제품은 본 과제에 나오지 않습니다.

계속하려면 스페이스바를 누르세요."""

TXT_TASK_START = """연습이 끝났습니다.

지금부터 본 과제입니다. 약 15분 걸립니다.
중간에 쉬는 구간이 한 번 있습니다.

계속하려면 스페이스바를 누르세요."""

TXT_BREAK = """잠시 쉬어 가겠습니다.

준비가 되면 스페이스바를 눌러 주세요."""

TXT_END = """과제가 끝났습니다.

이어서 사후 설문을 진행합니다.
연구자에게 알려 주세요."""

TXT_PAUSED = """일시 정지

계속하려면  N
종료하려면  Y"""


# ─────────────────────────────────────────────
#  실행 옵션
# ─────────────────────────────────────────────

ARGS = sys.argv[1:]
WINDOWED = "--windowed" in ARGS or "--record" in ARGS
AUTOPILOT = "--autopilot" in ARGS or "--record" in ARGS
RECORD_TO = None
if "--record" in ARGS:
    i = ARGS.index("--record")
    RECORD_TO = ARGS[i + 1] if i + 1 < len(ARGS) else "GPTC_task_demo"


class ParticipantQuit(Exception):
    """참가자나 실험자가 도중에 끝냈을 때."""


# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────


def linspace(start, stop, num):
    """numpy.linspace 자리."""
    if num == 1:
        return [start]
    step = (stop - start) / (num - 1)
    return [start + i * step for i in range(num)]


def max_run_ok(seq, max_run):
    """같은 값이 max_run번을 넘겨 연속하지 않는지."""
    run = 1
    for i in range(1, len(seq)):
        run = run + 1 if seq[i] == seq[i - 1] else 1
        if run > max_run:
            return False
    return True


def repeat_lag_ok(keys, min_lag):
    """같은 값이 다시 나올 때까지 min_lag 이상 떨어져 있는지."""
    last = {}
    for i, k in enumerate(keys):
        if k in last and i - last[k] < min_lag:
            return False
        last[k] = i
    return True


def has_batchim(word):
    """마지막 글자에 받침이 있는지. 조사를 고를 때 쓴다."""
    word = re.sub(r"[\]\)\}\s\.\,]+$", "", str(word).strip())
    if not word:
        return False
    ch = word[-1]
    if "가" <= ch <= "힣":
        return (ord(ch) - 0xAC00) % 28 != 0
    if ch.isdigit():
        return ch in "0136780"
    return ch.lower() in "lmnrg"


def read_csv(name):
    path = os.path.join(STIM_DIR, name)
    if not os.path.exists(path):
        raise SystemExit("자극 파일을 찾을 수 없습니다: %s" % path)
    with io.open(path, encoding="utf-8-sig", newline="") as fh:
        rows = [r for r in csv.DictReader(fh)
                if any((v or "").strip() for v in r.values())]
    if not rows:
        raise SystemExit("자극 파일이 비어 있습니다: %s" % path)
    return rows


# ─────────────────────────────────────────────
#  자극 만들기
# ─────────────────────────────────────────────


def sets_for(cat):
    """이 제품군에서 만들 세트 수. 연습 제품군 하나로 연습 시행을 다 채운다."""
    return CFG["n_practice"] if cat["block"] == "practice" \
        else CFG["sets_per_category"]


def load_stimuli():
    sources = read_csv("sources.csv")
    brands = [r["brand"].strip() for r in read_csv("brands.csv") if r["brand"].strip()]

    categories = []
    for r in read_csv("categories.csv"):
        cat = {k: (v or "").strip() for k, v in r.items()}
        cat["block"] = (cat.get("block") or "main").lower()
        if cat["block"] not in ("main", "practice"):
            raise SystemExit("block은 main 또는 practice여야 합니다: %s" % cat["block"])
        categories.append(cat)

    if not any(c["block"] == "practice" for c in categories):
        raise SystemExit("연습에 쓸 제품군이 없습니다. categories.csv의 block을 보세요.")

    details = {}
    for r in read_csv("details.csv"):
        code = r["category_code"].strip()
        dtype = r["detail_type"].strip().upper()
        if dtype not in ("UT", "HE"):
            raise SystemExit("detail_type은 UT 또는 HE여야 합니다: %s" % dtype)
        details.setdefault(code, []).append((dtype, r["text"].strip()))

    # 결정 국면 요약 문장. 추천 문구가 UT면 UT판, HE면 HE판이 나간다.
    phase2 = {}
    for r in read_csv("phase2.csv"):
        code = r["category_code"].strip()
        dtype = r["detail_type"].strip().upper()
        if dtype not in ("UT", "HE"):
            raise SystemExit("detail_type은 UT 또는 HE여야 합니다: %s" % dtype)
        phase2.setdefault(code, {})[dtype] = r["text"].strip()

    need = CFG["candidates_per_set"]
    for cat in categories:
        code = cat["category_code"]
        pool = details.get(code) or []
        if len(pool) < need:
            raise SystemExit(
                "%s의 특징이 %d개뿐입니다. 최소 %d개가 있어야 합니다."
                % (code, len(pool), need)
            )
        for dtype in ("UT", "HE"):
            if not phase2.get(code, {}).get(dtype):
                raise SystemExit("phase2.csv에 %s의 %s 문장이 없습니다." % (code, dtype))

    need_brands = sum(sets_for(c) for c in categories) * CFG["candidates_per_set"]
    if len(brands) < need_brands:
        raise SystemExit(
            "브랜드명이 %d개뿐입니다. 제품군 %d개를 채우려면 %d개가 있어야 합니다. "
            "tools_make_brands.py로 더 뽑으세요."
            % (len(brands), len(categories), need_brands)
        )
    return sources, categories, details, phase2, brands


def build_sets(categories, details, phase2, brands, rng):
    """제품군마다 후보 세트를 만든다.

    CSV가 주는 것은 제품군과 특징 풀뿐이다. 브랜드명, 브랜드와 특징의 짝,
    화면에 놓이는 순서, 가격은 전부 여기서 새로 뽑는다. 고정된 짝이 없어야
    특정 이름이나 특정 문구가 선호를 밀지 않는다.

    가격은 세트 단위로 하나만 정한다. 세 후보가 같은 가격을 쓰기 때문에 어느
    후보가 추천되든 결정 국면의 가격이 같고, 추천과 가격이 엉키지 않는다.
    """
    n_cand = CFG["candidates_per_set"]
    # 검수된 목록에서 참가자마다 다르게 뽑아 쓴다. 한 참가자 안에서는 안 겹친다.
    bag = list(brands)
    rng.shuffle(bag)
    sets = []

    for cat in sorted(categories, key=lambda c: c["category_code"]):
        code = cat["category_code"].strip()
        pool = details.get(code)
        if not pool:
            raise SystemExit("details.csv에 %s의 특징이 없습니다." % code)
        low, high = int(cat["price_low"]), int(cat["price_high"])

        for set_id in range(1, sets_for(cat) + 1):
            picked = rng.sample(pool, n_cand)               # 세트 안에서 특징 안 겹치게
            picked_brands = [bag.pop() for _ in range(n_cand)]
            rng.shuffle(picked_brands)                      # 이름과 특징의 짝을 섞는다
            cands = list(zip(picked_brands, picked))
            rng.shuffle(cands)                              # 화면 순서도 섞는다

            sets.append({
                "set_key": "%s_s%d" % (code, set_id),
                "category_code": code,
                "category_kr": cat["category_kr"].strip(),
                "major_class": cat["major_class"].strip(),
                "block": cat["block"],
                "set_id": set_id,
                "brands": [b for b, _ in cands],
                "details": [d[1] for _, d in cands],
                "detail_types": [d[0] for _, d in cands],
                "price": rng.randrange(low, high + 1, CFG["price_step"]),
                "phase2": dict(phase2[code]),
                "pool": pool,
            })
    return sets


# ─────────────────────────────────────────────
#  설계
# ─────────────────────────────────────────────


def assign_rec_positions(set_keys, rng):
    """세트마다 추천 제품이 놓일 줄을 고르게 나눠 준다.

    사전 설문에서 순위를 받지 않으므로 "추천이 몇 순위인가"는 알 수 없다.
    대신 화면 위치를 맞춰, 특정 정보원이 늘 맨 윗줄만 추천하는 쏠림을 막는다.
    """
    keys = list(set_keys)
    rng.shuffle(keys)
    positions = [(i % CFG["candidates_per_set"]) + 1 for i in range(len(keys))]
    rng.shuffle(positions)
    return dict(zip(keys, positions))


def deal_round_robin(keys, bag, reps, rng):
    """같은 정보원이 한 세트에 두 번 안 들어가게 bag을 keys에 나눠 준다.

    같은 정보원끼리 붙여 놓고 한 장씩 돌려 가며 나눈다. 한 정보원의 장수가
    세트 수를 안 넘으면 같은 세트로 두 장이 갈 수 없다.
    """
    counts = {}
    for code in bag:
        counts[code] = counts.get(code, 0) + 1
    if max(counts.values()) > len(keys):
        return None

    order = sorted(counts, key=lambda c: (-counts[c], rng.random()))
    flat = [c for c in order for _ in range(counts[c])]
    seats = list(keys)
    rng.shuffle(seats)

    out = {k: [] for k in keys}
    for i, code in enumerate(flat):
        out[seats[i % len(seats)]].append(code)
    for k in keys:
        if len(out[k]) != reps or len(set(out[k])) != reps:
            return None
        rng.shuffle(out[k])
    return out


def assign_sources(rec_positions, source_codes, rng, max_tries=20000):
    """세트마다 서로 다른 정보원을 repeats_per_set개 배정한다.

    추천 위치가 같은 세트들을 한 묶음으로 본다. 묶음마다 정보원별 배정 수를
    먼저 정하고, 그 수만큼을 세트에 흩는다. 배정 수를 정할 때 전체 합이 정보원마다
    똑같이 떨어지도록 남는 몫을 여유가 많은 정보원부터 준다. 그래서 위치 1·2·3이
    고르게 나뉘면서 전체 시행 수도 정보원마다 같아진다.

    묶음 크기가 정보원 수의 배수이던 시절에는 순열을 돌려도 균형이 맞았다.
    제품군이 21개로 늘면서 묶음이 7개가 되어 그 방법으로는 6~9시행까지 벌어진다.
    """
    codes = list(source_codes)
    n_src = len(codes)
    reps = CFG["repeats_per_set"]
    if reps > n_src:
        raise SystemExit("반복 수가 정보원 수보다 많으면 같은 세트에 같은 정보원이 겹칩니다.")

    by_pos = {}
    for key, pos in rec_positions.items():
        by_pos.setdefault(pos, []).append(key)
    for keys in by_pos.values():
        keys.sort()

    positions = sorted(by_pos)
    slots = {pos: len(by_pos[pos]) * reps for pos in positions}
    total = sum(slots.values())
    if total % n_src:
        raise SystemExit(
            "시행 %d개가 정보원 %d종으로 안 나뉩니다. 제품군 수나 반복 수를 보세요."
            % (total, n_src)
        )
    target = total // n_src

    for _ in range(max_tries):
        left = {c: target for c in codes}
        quota = {c: {} for c in codes}
        ok = True

        for pos in positions:
            base, rem = divmod(slots[pos], n_src)
            after = {c: left[c] - base for c in codes}
            order = sorted(codes, key=lambda c: (-after[c], rng.random()))
            extra = set(order[:rem])
            for c in codes:
                q = base + (1 if c in extra else 0)
                quota[c][pos] = q
                left[c] -= q
                if left[c] < 0:
                    ok = False
        if not ok or any(left[c] for c in codes):
            continue

        assignment = {}
        for pos in positions:
            bag = [c for c in codes for _ in range(quota[c][pos])]
            placed = deal_round_robin(by_pos[pos], bag, reps, rng)
            if placed is None:
                assignment = None
                break
            assignment.update(placed)
        if assignment is not None:
            return assignment

    raise SystemExit("정보원 배정 조건을 만족하는 조합을 찾지 못했습니다.")


def order_trials(trials, rng, max_tries=20000):
    """연속 제약과 반복 간격을 만족하는 순서로 늘어놓는다."""
    best = None
    for _ in range(max_tries):
        seq = list(trials)
        rng.shuffle(seq)
        if not max_run_ok([t["source_code"] for t in seq], CFG["max_run"]):
            continue
        if not max_run_ok([t["category_code"] for t in seq], CFG["max_run"]):
            continue
        if not max_run_ok([t["major_class"] for t in seq], CFG["max_run_major"]):
            continue
        if not repeat_lag_ok([t["set_key"] for t in seq], CFG["min_repeat_lag"]):
            best = seq
            continue
        return seq
    if best is not None:
        return best                     # 반복 간격만 못 맞춘 경우
    raise SystemExit("시행 순서 제약을 만족하는 배열을 찾지 못했습니다.")


def make_trial(cs, rec_pos, label, code, rep, block):
    rec_type = cs["detail_types"][rec_pos - 1]
    return {
        "block": block,
        "set_key": cs["set_key"],
        "category_code": cs["category_code"],
        "category_kr": cs["category_kr"],
        "major_class": cs["major_class"],
        "set_id": cs["set_id"],
        "source_code": code,
        "source_label": label,
        "repetition": rep,
        "price": cs["price"],
        "rec_position": rec_pos,
        "rec_brand": cs["brands"][rec_pos - 1],
        "rec_detail": cs["details"][rec_pos - 1],
        "rec_detail_type": rec_type,
        "brands": list(cs["brands"]),
        "details": list(cs["details"]),
        "detail_types": list(cs["detail_types"]),
        "phase2": cs["phase2"][rec_type],
    }


def build_trials(main_sets, practice_sets, sources, rng):
    rec_positions = assign_rec_positions([cs["set_key"] for cs in main_sets], rng)
    assignment = assign_sources(
        rec_positions, [s["source_code"] for s in sources], rng
    )
    label_of = {s["source_code"]: s["label"] for s in sources}
    by_key = {cs["set_key"]: cs for cs in main_sets}

    main = []
    for set_key, codes in assignment.items():
        cs = by_key[set_key]
        pos = rec_positions[set_key]
        for rep, code in enumerate(codes, start=1):
            main.append(make_trial(cs, pos, label_of[code], code, rep, "main"))
    main = order_trials(main, rng)

    pool = list(practice_sets)
    rng.shuffle(pool)
    practice = []
    for cs in pool[: CFG["n_practice"]]:
        pos = rng.randint(1, CFG["candidates_per_set"])
        practice.append(
            make_trial(cs, pos, PRACTICE_LABEL, "practice", 1, "practice")
        )
    return practice, main


# ─────────────────────────────────────────────
#  화면
# ─────────────────────────────────────────────


class Display:
    """창 하나와 거기 얹는 글자들. 응답 수집까지 여기서 한다."""

    def __init__(self, win, font, rng, recorder=None):
        self.win = win
        self.font = font
        self.rng = rng
        self.recorder = recorder          # 프레임 캡처. 녹화할 때만 들어온다
        self.pause_stim = self.text(TXT_PAUSED, height=CFG["h_instruction"],
                                    color=CFG["warn_color"])
        self.fix_stim = self.text("+", height=0.07)
        self._build_scale()

    # 만들기 ----------------------------------------------------------

    def text(self, message="", pos=(0, 0), height=None, color=None,
             wrap=1.4, bold=False):
        """가운데 정렬 글자 하나.

        TextStim이 아니라 TextBox2를 쓴다. TextStim은 pyglet의 win32 폰트
        경로를 타는데, PsychoPy가 윈도우에서 고정해 둔 pyglet 1.4.11이
        Python 3.12에서 깨진다. TextBox2는 freetype으로 직접 그린다.
        """
        return visual.TextBox2(
            self.win,
            text=message,
            pos=pos,
            letterHeight=height or CFG["h_feature"],
            color=color or CFG["text_color"],
            font=self.font,
            bold=bold,
            alignment="center",
            anchor="center",
            size=(wrap, None),
            units="height",
            editable=False,
        )

    def _build_scale(self):
        xs = linspace(CFG["scale_x_left"], CFG["scale_x_right"], CFG["scale_n"])
        self.circles = [
            visual.Circle(self.win, radius=CFG["circle_radius"], edges=64,
                          lineColor=CFG["text_color"],
                          lineWidth=CFG["circle_line_width"],
                          fillColor=None, pos=(x, CFG["scale_y"]), units="height")
            for x in xs
        ]
        self.numbers = [
            self.text(str(i + 1), pos=(x, CFG["numbers_y"]), height=CFG["h_number"])
            for i, x in enumerate(xs)
        ]
        self.left_desc = self.text("", pos=(CFG["scale_x_left"], CFG["desc_y"]),
                                   height=CFG["h_anchor"], wrap=0.5)
        self.right_desc = self.text("", pos=(CFG["scale_x_right"], CFG["desc_y"]),
                                    height=CFG["h_anchor"], wrap=0.5)
        self.question = self.text("", pos=(0, CFG["question_y"]),
                                  height=CFG["h_question"], wrap=1.5)
        self.binary_prompt = self.text("", pos=(0, CFG["question_y"]),
                                       height=CFG["h_question"], wrap=1.5)
        self.binary_labels = [
            self.text(OPT_BUY, pos=(-CFG["binary_x"], CFG["binary_y"]),
                      height=CFG["h_question"], bold=True),
            self.text(OPT_NOBUY, pos=(CFG["binary_x"], CFG["binary_y"]),
                      height=CFG["h_question"], bold=True),
        ]
        self.binary_boxes = [
            visual.Rect(self.win, width=CFG["binary_box_w"], height=CFG["binary_box_h"],
                        pos=(sign * CFG["binary_x"], CFG["binary_y"]),
                        lineColor=CFG["accent_color"],
                        lineWidth=CFG["circle_line_width"],
                        fillColor=None, units="height")
            for sign in (-1, 1)
        ]

    # 그리기 ----------------------------------------------------------

    def flip(self):
        self.win.flip()
        if self.recorder:
            self.recorder.maybe_capture(self.win)

    def draw(self, stims):
        for s in stims:
            s.draw()

    def hold(self, stims, duration):
        clock = core.Clock()
        while clock.getTime() < duration:
            self.draw(stims)
            self.flip()
            self.check_quit()

    def blank(self, duration):
        self.flip()
        clock = core.Clock()
        while clock.getTime() < duration:
            self.flip()

    def fixation(self, duration=None):
        """지터가 들어간 고정점. 실제로 머문 시간을 돌려준다."""
        dur = duration if duration is not None else \
            self.rng.uniform(CFG["fix_min"], CFG["fix_max"])
        clock = core.Clock()
        while clock.getTime() < dur:
            self.fix_stim.draw()
            self.flip()
            self.check_quit()
        return dur

    # 키 ------------------------------------------------------------

    def pause(self):
        """일시 정지 화면. Y면 종료, N이면 하던 데로 돌아간다."""
        event.clearEvents()
        while True:
            self.pause_stim.draw()
            self.flip()
            for key in event.getKeys(keyList=["y", "n"]):
                if key == "y":
                    raise ParticipantQuit("실험자 종료")
                event.clearEvents()
                return

    def check_quit(self):
        if not AUTOPILOT and event.getKeys(keyList=[CFG["key_quit"]]):
            self.pause()

    def instruction(self, body):
        """안내 화면. 스페이스바를 누를 때까지 머문다."""
        stim = self.text(body, pos=(0, 0.02), height=CFG["h_instruction"], wrap=1.5)
        if AUTOPILOT:
            self.hold([stim], self.rng.uniform(1.4, 2.2))
            return
        event.clearEvents()
        while True:
            stim.draw()
            self.flip()
            keys = event.getKeys(keyList=[CFG["key_advance"], CFG["key_quit"]])
            if CFG["key_quit"] in keys:
                self.pause()
            elif CFG["key_advance"] in keys:
                return

    # 응답 ----------------------------------------------------------

    def _scale_stims(self, context):
        return (list(context) + [self.question, self.left_desc, self.right_desc]
                + self.circles + self.numbers)

    def _paint(self, selected):
        for i, circ in enumerate(self.circles):
            circ.fillColor = CFG["accent_color"] if i == selected else None

    def likert(self, question, left, right, context=()):
        """점수(1~7)와 반응시간. 시간이 다 되면 (None, None).

        첫 입력은 방향과 무관하게 가운데(4)에서 시작한다. 어느 쪽 끝에서
        출발하느냐가 응답을 밀지 않게 하려는 것. Rowen 코드와 같은 동작이다.
        """
        self.question.text = question
        self.left_desc.text = left
        self.right_desc.text = right
        n, mid = CFG["scale_n"], CFG["scale_n"] // 2
        selected = None
        clock = core.Clock()

        if AUTOPILOT:
            target = self.rng.randint(0, n - 1)
            self._paint(None)
            self.hold(self._scale_stims(context), self.rng.uniform(0.3, 0.7))
            step = 1 if target >= mid else -1
            cur = mid
            selected = mid
            while cur != target:
                cur += step
                selected = cur
                self._paint(selected)
                self.hold(self._scale_stims(context), self.rng.uniform(0.12, 0.22))
            self._paint(selected)
            self.hold(self._scale_stims(context), CFG["feedback_flash"])
            return selected + 1, clock.getTime()

        event.clearEvents()
        while clock.getTime() < CFG["response_timeout"]:
            for key in event.getKeys(keyList=[CFG["key_left"], CFG["key_right"],
                                              CFG["key_confirm"], CFG["key_quit"]]):
                if key == CFG["key_quit"]:
                    self.pause()
                elif key == CFG["key_left"]:
                    selected = mid if selected is None else max(0, selected - 1)
                elif key == CFG["key_right"]:
                    selected = mid if selected is None else min(n - 1, selected + 1)
                elif key == CFG["key_confirm"] and selected is not None:
                    rt = clock.getTime()
                    self._paint(selected)
                    self.hold(self._scale_stims(context), CFG["feedback_flash"])
                    return selected + 1, rt
            self._paint(selected)
            self.draw(self._scale_stims(context))
            self.flip()
        return None, None

    def binary(self, prompt, context=()):
        """고른 문구와 반응시간. 시간이 다 되면 (None, None)."""
        self.binary_prompt.text = prompt
        options = (OPT_BUY, OPT_NOBUY)
        selected = None
        clock = core.Clock()

        def stims(sel):
            out = list(context) + [self.binary_prompt] + self.binary_labels
            if sel is not None:
                out.append(self.binary_boxes[sel])
            return out

        if AUTOPILOT:
            self.hold(stims(None), self.rng.uniform(0.4, 0.9))
            selected = self.rng.randint(0, 1)
            self.hold(stims(selected), self.rng.uniform(0.3, 0.6))
            return options[selected], clock.getTime()

        event.clearEvents()
        while clock.getTime() < CFG["response_timeout"]:
            for key in event.getKeys(keyList=[CFG["key_left"], CFG["key_right"],
                                              CFG["key_confirm"], CFG["key_quit"]]):
                if key == CFG["key_quit"]:
                    self.pause()
                elif key == CFG["key_left"]:
                    selected = 0
                elif key == CFG["key_right"]:
                    selected = 1
                elif key == CFG["key_confirm"] and selected is not None:
                    rt = clock.getTime()
                    self.hold(stims(selected), CFG["feedback_flash"])
                    return options[selected], rt
            self.draw(stims(selected))
            self.flip()
        return None, None


# ─────────────────────────────────────────────
#  시행 화면 조각
# ─────────────────────────────────────────────


def header(disp, trial):
    """맨 위 정보원 라벨.

    여섯 정보원의 화면 문구는 글자 그대로 같다. 바뀌는 것은 이 라벨뿐이라
    노란색으로 크게 띄운다.
    """
    return [
        disp.text(trial["source_label"], pos=(0, CFG["label_y"]),
                  height=CFG["h_label"], color=CFG["label_color"], bold=True),
    ]


def product_name(trial, brand):
    """화면에 나오는 제품 이름. 브랜드 뒤에 제품군을 붙인다.

    제품군을 따로 한 줄 띄우지 않고 여기서 합친다. "ECpM 바람막이"처럼
    실제 상품 목록에 가깝게 읽힌다.
    """
    return "%s %s" % (brand, trial["category_kr"])


def info_stims(disp, trial):
    stims = header(disp, trial)
    for i, (brand, detail) in enumerate(zip(trial["brands"], trial["details"])):
        stims.append(disp.text(
            "%s  -  %s" % (product_name(trial, brand), detail),
            pos=(0, CFG["candidates_top"] - i * CFG["candidate_gap"]),
            height=CFG["h_feature"], wrap=1.4,
        ))
    return stims


def decision_stims(disp, trial):
    stims = header(disp, trial)
    stims.append(disp.text(product_name(trial, trial["rec_brand"]),
                           pos=(0, CFG["brand_y"]),
                           height=CFG["h_brand"], bold=True))
    stims.append(disp.text("{:,}원".format(trial["price"]), pos=(0, CFG["price_y"]),
                           height=CFG["h_price"], bold=True))
    # 정보 국면에서 달고 있던 특징을 풀어 쓴 문장 한 줄.
    # 추천 문구가 UT면 UT판, HE면 HE판이 나간다.
    stims.append(disp.text(trial["phase2"],
                           pos=(0, CFG["detail_top"]),
                           height=CFG["h_detail"], color=CFG["dim_color"],
                           wrap=1.3))
    return stims


def run_trial(disp, trial, number, exp, clock):
    """한 시행.

    고정점 -> 정보 국면 -> 평정 -> 고정점 -> 결정 국면 -> 구매한다/구매하지 않는다 -> 구매 의향
    """
    exp.addData("TrialNumber", number)
    for key in ("block", "set_key", "category_code", "category_kr", "major_class",
                "set_id", "source_code", "source_label", "repetition", "price",
                "rec_position", "rec_brand", "rec_detail", "rec_detail_type",
                "phase2"):
        exp.addData(key, trial[key])
    exp.addData("Candidates", " | ".join(trial["brands"]))
    exp.addData("Details", " | ".join(trial["details"]))
    exp.addData("DetailTypes", " | ".join(trial["detail_types"]))
    exp.addData("N_UT", trial["detail_types"].count("UT"))
    exp.addData("N_HE", trial["detail_types"].count("HE"))

    # 정보 국면 ---------------------------------------------------
    # 글자 만드는 비용을 고정점 안으로 넣는다. 고정점이 끝나자마자 자극이
    # 떠야 하는데, 여기서 만들면 그만큼 제시가 늦어진다.
    stims = info_stims(disp, trial)
    exp.addData("fix1.started", clock.getTime())
    exp.addData("fix1.dur", round(disp.fixation(), 3))

    exp.addData("info.started", clock.getTime())
    disp.hold(stims, CFG["info_dur"])
    exp.addData("info.stopped", clock.getTime())

    score, rt = disp.likert(Q_INFO, Q_INFO_LEFT, Q_INFO_RIGHT, context=stims)
    exp.addData("InfoAccept", score if score is not None else "")
    exp.addData("InfoAccept_RT", round(rt, 4) if rt is not None else "")

    # 결정 국면 ---------------------------------------------------
    stims = decision_stims(disp, trial)
    exp.addData("fix2.started", clock.getTime())
    exp.addData("fix2.dur", round(disp.fixation(), 3))

    exp.addData("decision.started", clock.getTime())
    disp.hold(stims, CFG["decision_dur"])
    exp.addData("decision.stopped", clock.getTime())

    choice, rt = disp.binary(Q_BINARY, context=stims)
    exp.addData("PurchaseChoice", choice if choice is not None else "")
    exp.addData("PurchaseChoice_bin",
                "" if choice is None else int(choice == OPT_BUY))
    exp.addData("PurchaseChoice_RT", round(rt, 4) if rt is not None else "")

    intent, rt = disp.likert(Q_INTENT, Q_INTENT_LEFT, Q_INTENT_RIGHT, context=stims)
    exp.addData("PurchaseIntent", intent if intent is not None else "")
    exp.addData("PurchaseIntent_RT", round(rt, 4) if rt is not None else "")

    exp.nextEntry()


# ─────────────────────────────────────────────
#  참가자 정보
# ─────────────────────────────────────────────


def ask_participant():
    """참가자 ID, 연령, 성별만 받는다.

    제품군을 빼지 않는 판이라 제외 목록을 묻지 않는다. 사전 설문의 제품군
    관심도는 분석에서 공변량으로 쓰고 과제 구성에는 넣지 않는다.
    """
    info = {"참가자 ID": "", "연령": "", "성별": ["여", "남", "기타/무응답"]}
    order = ["참가자 ID", "연령", "성별"]

    if AUTOPILOT:
        return {"참가자 ID": "DEMO01", "연령": "23", "성별": "여"}

    dlg = gui.DlgFromDict(dictionary=info, title="GPTC 과제 (0818)", order=order)
    if not dlg.OK:
        core.quit()
    if not str(info["참가자 ID"]).strip():
        raise SystemExit("참가자 ID를 입력해야 합니다.")
    return info


# ─────────────────────────────────────────────
#  main
# ─────────────────────────────────────────────


def main():
    sources, categories, details, phase2, brands = load_stimuli()
    info = ask_participant()
    pid = str(info["참가자 ID"]).strip()

    # 참가자 ID로 시드를 고정한다. 같은 참가자를 다시 돌리면 같은 배치가 나온다.
    rng = random.Random("%s|%s" % (EXP_NAME, pid))

    all_sets = build_sets(categories, details, phase2, brands, rng)
    main_sets = [cs for cs in all_sets if cs["block"] == "main"]
    practice_sets = [cs for cs in all_sets if cs["block"] == "practice"]
    practice, trials = build_trials(main_sets, practice_sets, sources, rng)

    os.makedirs(DATA_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%Hh%M.%S")
    base = os.path.join(DATA_DIR, "%s_%s_%s" % (pid, EXP_NAME, stamp))

    exp = data.ExperimentHandler(
        name=EXP_NAME,
        extraInfo={"participant": pid, "age": info["연령"], "sex": info["성별"],
                   "date": stamp},
        dataFileName=base,
        savePickle=False,
        saveWideText=False,   # finally에서 직접 한 번만 쓴다
    )

    win = visual.Window(
        size=(1280, 800) if WINDOWED else (1920, 1080),
        fullscr=not WINDOWED,
        color=CFG["bg_color"],
        units="height",
        allowGUI=WINDOWED,
        winType="pyglet",
    )
    win.mouseVisible = WINDOWED

    font = CFG["font_candidates"][0]
    try:
        from psychopy.visual.textbox2.fontmanager import FontManager

        available = set(FontManager().getFontFamilyNames())
        font = next((f for f in CFG["font_candidates"] if f in available), font)
    except Exception:
        pass

    recorder = None
    if RECORD_TO:
        from recorder_frames import FrameRecorder

        recorder = FrameRecorder(RECORD_TO)

    disp = Display(win, font, rng, recorder)
    clock = core.Clock()
    completed = False

    try:
        disp.instruction(TXT_WELCOME)
        disp.instruction(TXT_KEYS)
        disp.instruction(TXT_PRACTICE)
        for i, t in enumerate(practice, start=1):
            run_trial(disp, t, i, exp, clock)

        disp.instruction(TXT_TASK_START)
        disp.fixation(CFG["intro_fix_dur"])

        half = len(trials) // 2
        for i, t in enumerate(trials, start=1):
            run_trial(disp, t, i, exp, clock)
            if i == half and i < len(trials):
                disp.instruction(TXT_BREAK)

        disp.instruction(TXT_END)
        completed = True

    except ParticipantQuit:
        pass
    finally:
        meta = {"participant": pid, "experiment": EXP_NAME, "date": stamp,
                "font": font, "completed": completed,
                "n_practice": len(practice), "n_trials": len(trials)}
        with io.open(base + "_meta.json", "w", encoding="utf-8") as fh:
            fh.write(json.dumps(meta, ensure_ascii=False, indent=2))
        exp.saveAsWideText(base + ".csv", delim=",", encoding="utf-8-sig",
                           fileCollisionMethod="overwrite")
        if recorder:
            recorder.finish()
        win.mouseVisible = True
        try:
            win.close()
        except Exception:
            pass
        core.quit()


if __name__ == "__main__":
    main()
