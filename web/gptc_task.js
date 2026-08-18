// 과제 실행부. PsychoJS로 창을 열고 자극을 띄우고 응답을 받는다.
// GPTC_task.py 의 Display 클래스와 run_trial 이 하던 일을 그대로 옮겼다.
//
// 흐름은 제너레이터로 짰다. taskFlow()가 화면 하나를 yield하면 프레임 함수가
// 그 화면을 끝날 때까지 돌리고, 결과를 next()로 되돌려 준다. Builder가 뽑아
// 내는 begin/eachFrame/end 세 벌을 안 써도 파이썬 쪽 순서와 나란히 읽힌다.

import { core, data, util, visual } from "./lib/psychojs-2026.2.1.js";
import { STIM } from "./gptc_stim.js";
import { VARIANTS, TXT, Q } from "./gptc_config.js";
import { buildDesign, makeRng } from "./gptc_design.js";

const { PsychoJS } = core;
const { ExperimentHandler } = data;
const { Scheduler } = util;

const KEY = {
	left: "left", right: "right", confirm: "return",
	advance: "space", quit: "escape",
};

class ParticipantQuit extends Error {}

// ── 화면 조각 ────────────────────────────────────────────

/**
 * 자극을 미리 만들어 두고 글자만 갈아 끼운다.
 * 시행마다 새로 만들면 첫 프레임이 늦어서 제시 시간이 흔들린다.
 */
function makeStims(win, cfg) {
	const text = (opts) => new visual.TextStim(Object.assign({
		win, units: "height", font: cfg.font, alignHoriz: "center",
		height: cfg.h_feature, color: new util.Color(cfg.text_color),
		wrapWidth: 1.4, text: "",
	}, opts));

	const s = {
		fix: text({ name: "fix", text: "+", height: 0.07 }),
		instruction: text({ name: "instr", pos: [0, 0.02], height: cfg.h_instruction, wrapWidth: 1.5 }),
		paused: text({ name: "paused", text: TXT.paused, height: cfg.h_instruction,
			color: new util.Color(cfg.warn_color), wrapWidth: 1.5 }),
		label: text({ name: "label", pos: [0, cfg.label_y], height: cfg.h_label,
			color: new util.Color(cfg.label_color), bold: true }),
		candidates: [], details: [],
		brand: text({ name: "brand", pos: [0, cfg.brand_y], height: cfg.h_brand, bold: true }),
		price: text({ name: "price", pos: [0, cfg.price_y], height: cfg.h_price, bold: true }),
		question: text({ name: "q", pos: [0, cfg.question_y], height: cfg.h_question, wrapWidth: 1.5 }),
		leftDesc: text({ name: "ld", pos: [cfg.scale_x_left, cfg.desc_y], height: cfg.h_anchor, wrapWidth: 0.5 }),
		rightDesc: text({ name: "rd", pos: [cfg.scale_x_right, cfg.desc_y], height: cfg.h_anchor, wrapWidth: 0.5 }),
		binaryPrompt: text({ name: "bp", pos: [0, cfg.question_y], height: cfg.h_question, wrapWidth: 1.5 }),
		circles: [], numbers: [], binaryLabels: [], binaryBoxes: [],
		marker: null,
	};

	for (let i = 0; i < cfg.candidates_per_set; i++) {
		s.candidates.push(text({
			name: "cand" + i, pos: [0, cfg.candidates_top - i * cfg.candidate_gap],
			height: cfg.h_feature,
		}));
	}
	// 기존판은 세 줄, 0818판은 한 줄만 쓴다. 슬롯은 넉넉히 세 개 잡아 둔다.
	for (let i = 0; i < 3; i++) {
		s.details.push(text({
			name: "detail" + i, pos: [0, cfg.detail_top - i * cfg.detail_gap],
			height: cfg.h_detail, color: new util.Color(cfg.dim_color), wrapWidth: 1.3,
		}));
	}

	const xs = util.linspace(cfg.scale_x_left, cfg.scale_x_right, cfg.scale_n);
	s.scaleX = xs;
	// 고른 자리를 채워진 원 하나로 표시한다. 원마다 fillColor를 껐다 켜는 것보다
	// 자리만 옮기는 쪽이 그릴 것도 적고 API도 덜 탄다.
	s.marker = new visual.Polygon({
		win, name: "marker", edges: 64, radius: cfg.circle_radius, units: "height",
		lineColor: new util.Color(cfg.accent_color), lineWidth: cfg.circle_line_width,
		fillColor: new util.Color(cfg.accent_color), pos: [xs[0], cfg.scale_y],
	});
	for (let i = 0; i < cfg.scale_n; i++) {
		s.circles.push(new visual.Polygon({
			win, name: "circ" + i, edges: 64, radius: cfg.circle_radius, units: "height",
			lineColor: new util.Color(cfg.text_color), lineWidth: cfg.circle_line_width,
			fillColor: undefined, pos: [xs[i], cfg.scale_y],
		}));
		s.numbers.push(text({ name: "num" + i, text: String(i + 1),
			pos: [xs[i], cfg.numbers_y], height: cfg.h_number }));
	}
	[Q.optBuy, Q.optNoBuy].forEach((opt, i) => {
		const sign = i === 0 ? -1 : 1;
		s.binaryLabels.push(text({ name: "bl" + i, text: opt,
			pos: [sign * cfg.binary_x, cfg.binary_y], height: cfg.h_question, bold: true }));
		s.binaryBoxes.push(new visual.Rect({
			win, name: "bb" + i, width: cfg.binary_box_w, height: cfg.binary_box_h,
			pos: [sign * cfg.binary_x, cfg.binary_y], units: "height",
			lineColor: new util.Color(cfg.accent_color), lineWidth: cfg.circle_line_width,
			fillColor: undefined,
		}));
	});
	return s;
}

function productName(trial, brand) {
	return brand + " " + trial.categoryKr;
}

/** 정보 국면 화면. 정보원 라벨과 후보 세 줄. */
function infoStims(s, cfg, trial) {
	s.label.setText(trial.sourceLabel);
	const out = [s.label];
	trial.brands.forEach((brand, i) => {
		s.candidates[i].setText(productName(trial, brand) + "  -  " + trial.details[i]);
		out.push(s.candidates[i]);
	});
	return out;
}

/** 결정 국면 화면. 기존판은 특징 세 줄, 0818판은 요약 문장 한 줄. */
function decisionStims(s, cfg, trial) {
	s.label.setText(trial.sourceLabel);
	s.brand.setText(productName(trial, trial.recBrand));
	s.price.setText(trial.price.toLocaleString("ko-KR") + "원");
	const out = [s.label, s.brand, s.price];
	const lines = cfg.n_extra_details
		? [trial.recDetail].concat(trial.extra).map((t) => "· " + t)
		: [trial.phase2];
	lines.forEach((line, i) => {
		s.details[i].setText(line);
		out.push(s.details[i]);
	});
	return out;
}

// ── 화면 하나 (제너레이터가 yield 하는 것) ────────────────

const show = (stims) => stims.forEach((st) => st.setAutoDraw(true));
const hide = (stims) => stims.forEach((st) => st.setAutoDraw(false));

/** 정해진 시간만큼 띄워 두기. */
function hold(stims, duration) {
	return {
		stims,
		enter: () => show(stims),
		exit: () => hide(stims),
		frame: (t) => (t >= duration ? true : undefined),
	};
}

/** 지터가 들어간 고정점. 실제로 머문 시간을 돌려준다. */
function fixation(s, cfg, rng, duration) {
	const dur = duration !== undefined ? duration
		: cfg.fix_min + rng.random() * (cfg.fix_max - cfg.fix_min);
	return {
		stims: [s.fix],
		enter: () => show([s.fix]),
		exit: () => hide([s.fix]),
		frame: (t) => (t >= dur ? dur : undefined),
	};
}

/** 안내 화면. 스페이스바를 누를 때까지 머문다. */
function instruction(s, cfg, io, body) {
	s.instruction.setText(body);
	return {
		stims: [s.instruction],
		enter: () => { show([s.instruction]); io.clear(); },
		exit: () => hide([s.instruction]),
		frame: () => (io.pressed(KEY.advance) ? true : undefined),
	};
}

/**
 * 리커트 7점. 점수(1~7)와 반응시간을 돌려준다. 시간이 다 되면 둘 다 null.
 *
 * 첫 입력은 방향과 무관하게 가운데(4)에서 시작한다. 어느 쪽 끝에서 출발하느냐가
 * 응답을 밀지 않게 하려는 것. 파이썬판과 같은 동작이다.
 */
function likert(s, cfg, io, question, left, right, context) {
	s.question.setText(question);
	s.leftDesc.setText(left);
	s.rightDesc.setText(right);
	const n = cfg.scale_n;
	const mid = Math.floor(n / 2);
	const stims = context.concat([s.question, s.leftDesc, s.rightDesc],
		s.circles, s.numbers);

	let selected = null;
	let confirmedAt = null;
	const paint = () => {
		if (selected === null) { s.marker.setAutoDraw(false); return; }
		s.marker.setPos([s.scaleX[selected], cfg.scale_y]);
		s.marker.setAutoDraw(true);
	};

	return {
		stims: stims.concat([s.marker]),
		enter: () => { selected = null; paint(); show(stims); io.clear(); },
		exit: () => { selected = null; paint(); hide(stims); s.marker.setAutoDraw(false); },
		frame: (t) => {
			if (confirmedAt !== null) {
				return t >= confirmedAt + cfg.feedback_flash
					? { score: selected + 1, rt: confirmedAt } : undefined;
			}
			for (const key of io.keys([KEY.left, KEY.right, KEY.confirm])) {
				if (key === KEY.left) {
					selected = selected === null ? mid : Math.max(0, selected - 1);
				} else if (key === KEY.right) {
					selected = selected === null ? mid : Math.min(n - 1, selected + 1);
				} else if (key === KEY.confirm && selected !== null) {
					confirmedAt = t;
				}
			}
			paint();
			if (t >= cfg.response_timeout) return { score: null, rt: null };
			return undefined;
		},
	};
}

/** 구매한다 / 구매하지 않는다. 고른 문구와 반응시간. */
function binary(s, cfg, io, prompt, context) {
	s.binaryPrompt.setText(prompt);
	const options = [Q.optBuy, Q.optNoBuy];
	const base = context.concat([s.binaryPrompt], s.binaryLabels);
	let selected = null;
	let confirmedAt = null;
	const paint = () => s.binaryBoxes.forEach((b, i) => b.setAutoDraw(i === selected));

	return {
		stims: base.concat(s.binaryBoxes),
		enter: () => { selected = null; show(base); paint(); io.clear(); },
		exit: () => { selected = null; hide(base); hide(s.binaryBoxes); },
		frame: (t) => {
			if (confirmedAt !== null) {
				return t >= confirmedAt + cfg.feedback_flash
					? { choice: options[selected], rt: confirmedAt } : undefined;
			}
			for (const key of io.keys([KEY.left, KEY.right, KEY.confirm])) {
				if (key === KEY.left) selected = 0;
				else if (key === KEY.right) selected = 1;
				else if (key === KEY.confirm && selected !== null) confirmedAt = t;
			}
			paint();
			if (t >= cfg.response_timeout) return { choice: null, rt: null };
			return undefined;
		},
	};
}

// ── 한 시행 ──────────────────────────────────────────────

function* runTrial(s, cfg, io, exp, trial, number, clock) {
	exp.addData("TrialNumber", number);
	for (const [col, key] of [
		["block", "block"], ["set_key", "setKey"], ["category_code", "categoryCode"],
		["category_kr", "categoryKr"], ["major_class", "majorClass"], ["set_id", "setId"],
		["source_code", "sourceCode"], ["source_label", "sourceLabel"],
		["repetition", "repetition"], ["price", "price"], ["rec_position", "recPosition"],
		["rec_brand", "recBrand"], ["rec_detail", "recDetail"],
		["rec_detail_type", "recDetailType"],
	]) {
		exp.addData(col, trial[key]);
	}
	exp.addData("Candidates", trial.brands.join(" | "));
	exp.addData("Details", trial.details.join(" | "));
	exp.addData("DetailTypes", trial.detailTypes.join(" | "));
	exp.addData("N_UT", trial.detailTypes.filter((d) => d === "UT").length);
	exp.addData("N_HE", trial.detailTypes.filter((d) => d === "HE").length);
	if (cfg.n_extra_details) exp.addData("ExtraLines", trial.extra.join(" | "));
	else exp.addData("phase2", trial.phase2);

	// 정보 국면
	const info = infoStims(s, cfg, trial);
	exp.addData("fix1.started", clock.getTime());
	exp.addData("fix1.dur", Math.round((yield fixation(s, cfg, io.rng)) * 1000) / 1000);

	exp.addData("info.started", clock.getTime());
	yield hold(info, cfg.info_dur);
	exp.addData("info.stopped", clock.getTime());

	const accept = yield likert(s, cfg, io, Q.info, Q.infoLeft, Q.infoRight, info);
	exp.addData("InfoAccept", accept.score === null ? "" : accept.score);
	exp.addData("InfoAccept_RT", accept.rt === null ? "" : Math.round(accept.rt * 1e4) / 1e4);

	// 결정 국면
	const decision = decisionStims(s, cfg, trial);
	exp.addData("fix2.started", clock.getTime());
	exp.addData("fix2.dur", Math.round((yield fixation(s, cfg, io.rng)) * 1000) / 1000);

	exp.addData("decision.started", clock.getTime());
	yield hold(decision, cfg.decision_dur);
	exp.addData("decision.stopped", clock.getTime());

	const choice = yield binary(s, cfg, io, Q.binary, decision);
	exp.addData("PurchaseChoice", choice.choice === null ? "" : choice.choice);
	exp.addData("PurchaseChoice_bin", choice.choice === null ? "" : (choice.choice === Q.optBuy ? 1 : 0));
	exp.addData("PurchaseChoice_RT", choice.rt === null ? "" : Math.round(choice.rt * 1e4) / 1e4);

	const intent = yield likert(s, cfg, io, Q.intent, Q.intentLeft, Q.intentRight, decision);
	exp.addData("PurchaseIntent", intent.score === null ? "" : intent.score);
	exp.addData("PurchaseIntent_RT", intent.rt === null ? "" : Math.round(intent.rt * 1e4) / 1e4);

	exp.nextEntry();
}

function* taskFlow(s, cfg, io, exp, design, clock) {
	yield instruction(s, cfg, io, TXT.welcome);
	yield instruction(s, cfg, io, TXT.keys);
	yield instruction(s, cfg, io, TXT.practice);
	for (let i = 0; i < design.practice.length; i++) {
		yield* runTrial(s, cfg, io, exp, design.practice[i], i + 1, clock);
	}

	yield instruction(s, cfg, io, TXT.taskStart);
	yield fixation(s, cfg, io.rng, cfg.intro_fix_dur);

	const half = Math.floor(design.trials.length / 2);
	for (let i = 0; i < design.trials.length; i++) {
		yield* runTrial(s, cfg, io, exp, design.trials[i], i + 1, clock);
		if (i + 1 === half && i + 1 < design.trials.length) {
			yield instruction(s, cfg, io, TXT.breakText);
		}
	}
	yield instruction(s, cfg, io, TXT.end);
}

// ── 실행 ─────────────────────────────────────────────────

export function runTask(variantName, options = {}) {
	const cfg = VARIANTS[variantName];
	if (!cfg) throw new Error("모르는 판입니다: " + variantName);
	const stim = STIM[cfg.stim_key];
	const expName = cfg.exp_name;
	const windowed = options.windowed || new URLSearchParams(location.search).has("windowed");

	const expInfo = { "참가자 ID": "", "연령": "", "성별": ["여", "남", "기타/무응답"] };

	const psychoJS = new PsychoJS({ debug: false });
	psychoJS.openWindow({
		fullscr: !windowed,
		color: new util.Color(cfg.bg_color),
		units: "height",
		waitBlanking: true,
	});
	psychoJS.schedule(psychoJS.gui.DlgFromDict({ dictionary: expInfo, title: cfg.title }));

	const flowScheduler = new Scheduler(psychoJS);
	const cancelScheduler = new Scheduler(psychoJS);
	psychoJS.scheduleCondition(
		() => psychoJS.gui.dialogComponent.button === "OK", flowScheduler, cancelScheduler);

	let s, io, exp, flow, clock, stageClock;
	let current = null, pending, paused = false, completed = false;

	flowScheduler.add(function setup() {
		const pid = String(expInfo["참가자 ID"] || "").trim();
		if (!pid) {
			alert("참가자 ID를 입력해야 합니다.");
			return Scheduler.Event.QUIT;
		}
		expInfo["date"] = util.MonotonicClock.getDateStr();
		expInfo["expName"] = expName;
		expInfo["participant"] = pid;
		psychoJS.experiment.dataFileName = pid + "_" + expName + "_" + expInfo["date"];

		// 참가자 ID로 시드를 고정한다. 같은 참가자를 다시 돌리면 같은 배치가 나온다.
		const rng = makeRng(expName + "|" + pid);
		const design = buildDesign(cfg, stim, expName + "|" + pid);

		exp = psychoJS.experiment;
		s = makeStims(psychoJS.window, cfg);
		io = {
			rng,
			keys: (keyList) => psychoJS.eventManager.getKeys({ keyList }),
			pressed: (k) => psychoJS.eventManager.getKeys({ keyList: [k] }).length > 0,
			clear: () => psychoJS.eventManager.clearEvents(),
		};
		clock = new util.Clock();
		stageClock = new util.Clock();
		flow = taskFlow(s, cfg, io, exp, design, clock);
		return Scheduler.Event.NEXT;
	});

	flowScheduler.add(function frame() {
		// Esc는 어디서든 받는다. Y면 종료, N이면 하던 데로 돌아간다.
		if (paused) {
			for (const key of psychoJS.eventManager.getKeys({ keyList: ["y", "n"] })) {
				s.paused.setAutoDraw(false);
				if (key === "y") return Scheduler.Event.NEXT;
				if (current) show(current.stims || []);
				paused = false;
				psychoJS.eventManager.clearEvents();
			}
			return Scheduler.Event.FLIP_REPEAT;
		}
		if (psychoJS.eventManager.getKeys({ keyList: [KEY.quit] }).length) {
			// 파이썬판과 같다. 멈춘 동안에도 그 화면의 시계는 계속 간다.
			// 끊고 들어간 시행은 어차피 못 쓴다.
			paused = true;
			if (current) hide(current.stims || []);
			s.paused.setAutoDraw(true);
			psychoJS.eventManager.clearEvents();
			return Scheduler.Event.FLIP_REPEAT;
		}

		if (current === null) {
			let step;
			try {
				step = flow.next(pending);
			} catch (err) {
				if (err instanceof ParticipantQuit) return Scheduler.Event.NEXT;
				throw err;
			}
			if (step.done) {
				completed = true;
				return Scheduler.Event.NEXT;
			}
			current = step.value;
			current.enter();
			stageClock.reset();
		}
		const result = current.frame(stageClock.getTime());
		if (result === undefined) return Scheduler.Event.FLIP_REPEAT;
		current.exit();
		pending = result;
		current = null;
		return Scheduler.Event.FLIP_REPEAT;
	});

	flowScheduler.add(async function finish() {
		psychoJS.window.close();
		await psychoJS.quit({
			message: "과제가 끝났습니다. 내려받은 CSV를 연구자에게 전달해 주세요.",
			isCompleted: completed,
		});
		return Scheduler.Event.QUIT;
	});

	cancelScheduler.add(async function cancelled() {
		psychoJS.window.close();
		await psychoJS.quit({ message: "취소되었습니다.", isCompleted: false });
		return Scheduler.Event.QUIT;
	});

	psychoJS.start({ expName, expInfo, resources: [] });
	return psychoJS;
}
