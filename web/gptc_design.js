// 설계 로직. GPTC_task.py 와 GPTC_task_0818.py 의 무작위화 부분을 그대로 옮겼다.
// 화면과 응답은 gptc_task.js 에 있다. 이 파일은 psychojs를 안 쓴다.
//
// 파이썬판과 배치가 같지는 않다. 파이썬의 random.Random 은 메르센 트위스터라
// 자바스크립트에서 같은 수열을 재현할 수 없다. 각 판 안에서는 참가자 ID를 시드로
// 잡아 재현되지만, 같은 ID를 파이썬판과 웹판에 넣으면 다른 배치가 나온다.

// ── 시드 난수 ────────────────────────────────────────────

function hashSeed(text) {
	let h = 2166136261 >>> 0;
	for (let i = 0; i < text.length; i++) {
		h ^= text.charCodeAt(i);
		h = Math.imul(h, 16777619) >>> 0;
	}
	return h >>> 0;
}

/** mulberry32. 시드 하나로 같은 수열이 나온다. */
export function makeRng(seedText) {
	let a = hashSeed(String(seedText));
	const next = () => {
		a = (a + 1831565813) >>> 0;
		let t = Math.imul(a ^ (a >>> 15), 1 | a);
		t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
		return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
	};
	return {
		random: next,
		/** low 이상 high 이하 정수 */
		randint: (low, high) => low + Math.floor(next() * (high - low + 1)),
		/** low 이상 high 이하에서 step 간격 */
		randrange: (low, high, step) => {
			const n = Math.floor((high - low) / step) + 1;
			return low + step * Math.floor(next() * n);
		},
		/** 제자리 섞기 (Fisher-Yates) */
		shuffle: (arr) => {
			for (let i = arr.length - 1; i > 0; i--) {
				const j = Math.floor(next() * (i + 1));
				[arr[i], arr[j]] = [arr[j], arr[i]];
			}
			return arr;
		},
		/** 중복 없이 k개 뽑기 */
		sample: (arr, k) => {
			const pool = arr.slice();
			const out = [];
			for (let i = 0; i < k; i++) {
				out.push(pool.splice(Math.floor(next() * pool.length), 1)[0]);
			}
			return out;
		},
	};
}

// ── 제약 검사 ────────────────────────────────────────────

/** 같은 값이 maxRun번을 넘겨 연속하지 않는지. */
export function maxRunOk(seq, maxRun) {
	let run = 1;
	for (let i = 1; i < seq.length; i++) {
		run = seq[i] === seq[i - 1] ? run + 1 : 1;
		if (run > maxRun) return false;
	}
	return true;
}

/** 같은 값이 다시 나올 때까지 minLag 이상 떨어져 있는지. */
export function repeatLagOk(keys, minLag) {
	const last = new Map();
	for (let i = 0; i < keys.length; i++) {
		if (last.has(keys[i]) && i - last.get(keys[i]) < minLag) return false;
		last.set(keys[i], i);
	}
	return true;
}

// ── 자극 고르기 ──────────────────────────────────────────

function setsFor(cfg, cat) {
	return cat.block === "practice" ? cfg.n_practice : cfg.sets_per_category;
}

/**
 * 제품군마다 후보 세트를 만든다.
 *
 * CSV가 주는 것은 제품군과 특징 풀뿐이다. 브랜드명, 브랜드와 특징의 짝, 화면에
 * 놓이는 순서, 가격은 전부 여기서 새로 뽑는다. 가격은 세트 단위로 하나만 정해서
 * 어느 후보가 추천되든 결정 국면의 가격이 같게 둔다.
 */
export function buildSets(cfg, stim, rng) {
	const nCand = cfg.candidates_per_set;
	const bag = rng.shuffle(stim.brands.slice());
	const sets = [];

	const cats = stim.categories.slice().sort((a, b) => (a.code < b.code ? -1 : 1));
	for (const cat of cats) {
		const pool = stim.details[cat.code];
		if (!pool) throw new Error("details에 " + cat.code + " 의 특징이 없습니다.");

		for (let setId = 1; setId <= setsFor(cfg, cat); setId++) {
			const picked = rng.sample(pool, nCand);          // 세트 안에서 특징 안 겹치게
			const pickedBrands = [];
			for (let i = 0; i < nCand; i++) pickedBrands.push(bag.pop());
			rng.shuffle(pickedBrands);                       // 이름과 특징의 짝을 섞는다
			const cands = pickedBrands.map((b, i) => [b, picked[i]]);
			rng.shuffle(cands);                              // 화면 순서도 섞는다

			sets.push({
				setKey: cat.code + "_s" + setId,
				categoryCode: cat.code,
				categoryKr: cat.kr,
				majorClass: cat.major,
				block: cat.block,
				setId: setId,
				brands: cands.map((c) => c[0]),
				details: cands.map((c) => c[1][1]),
				detailTypes: cands.map((c) => c[1][0]),
				price: rng.randrange(cat.low, cat.high, cfg.price_step),
				phase2: stim.phase2 ? Object.assign({}, stim.phase2[cat.code]) : null,
				pool: pool,
			});
		}
	}
	return sets;
}

/**
 * 결정 국면에서 추천 제품 밑에 덧붙일 줄. 기존판에서만 쓴다.
 * 세트에 이미 쓰인 특징은 빼고 남은 풀에서 뽑아, 한 화면에 같은 문구가 두 번
 * 나오지 않게 한다.
 */
export function extraLines(cfg, cs, rng) {
	const used = new Set(cs.details);
	const rest = cs.pool.map((d) => d[1]).filter((t) => !used.has(t));
	rng.shuffle(rest);
	return rest.slice(0, cfg.n_extra_details);
}

// ── 정보원 배정 ──────────────────────────────────────────

/**
 * 세트마다 추천 제품이 놓일 줄을 고르게 나눠 준다.
 * 특정 정보원이 늘 맨 윗줄만 추천하는 쏠림을 막는다.
 */
export function assignRecPositions(cfg, setKeys, rng) {
	const keys = rng.shuffle(setKeys.slice());
	const positions = keys.map((_, i) => (i % cfg.candidates_per_set) + 1);
	rng.shuffle(positions);
	const out = new Map();
	keys.forEach((k, i) => out.set(k, positions[i]));
	return out;
}

/**
 * 같은 정보원이 한 세트에 두 번 안 들어가게 bag을 keys에 나눠 준다.
 * 같은 정보원끼리 붙여 놓고 한 장씩 돌려 가며 나눈다. 한 정보원의 장수가
 * 세트 수를 안 넘으면 같은 세트로 두 장이 갈 수 없다.
 */
function dealRoundRobin(keys, bag, reps, rng) {
	const counts = new Map();
	for (const code of bag) counts.set(code, (counts.get(code) || 0) + 1);
	if (Math.max(...counts.values()) > keys.length) return null;

	const order = [...counts.keys()].sort((a, b) => {
		const d = counts.get(b) - counts.get(a);
		return d !== 0 ? d : rng.random() - 0.5;
	});
	const flat = [];
	for (const code of order) {
		for (let i = 0; i < counts.get(code); i++) flat.push(code);
	}
	const seats = rng.shuffle(keys.slice());

	const out = new Map(keys.map((k) => [k, []]));
	flat.forEach((code, i) => out.get(seats[i % seats.length]).push(code));
	for (const k of keys) {
		const got = out.get(k);
		if (got.length !== reps || new Set(got).size !== reps) return null;
		rng.shuffle(got);
	}
	return out;
}

/**
 * 세트마다 서로 다른 정보원을 repeats_per_set개 배정한다.
 *
 * 추천 위치가 같은 세트들을 한 묶음으로 본다. 묶음마다 정보원별 배정 수를 먼저
 * 정하고, 그 수만큼을 세트에 흩는다. 배정 수를 정할 때 전체 합이 정보원마다
 * 똑같이 떨어지도록 남는 몫을 여유가 많은 정보원부터 준다.
 */
export function assignSources(cfg, recPositions, sourceCodes, rng, maxTries = 20000) {
	const codes = sourceCodes.slice();
	const nSrc = codes.length;
	const reps = cfg.repeats_per_set;
	if (reps > nSrc) throw new Error("반복 수가 정보원 수보다 많습니다.");

	const byPos = new Map();
	for (const [key, pos] of recPositions) {
		if (!byPos.has(pos)) byPos.set(pos, []);
		byPos.get(pos).push(key);
	}
	for (const keys of byPos.values()) keys.sort();

	const positions = [...byPos.keys()].sort((a, b) => a - b);
	const slots = new Map(positions.map((p) => [p, byPos.get(p).length * reps]));
	const total = [...slots.values()].reduce((a, b) => a + b, 0);
	if (total % nSrc) {
		throw new Error("시행 " + total + "개가 정보원 " + nSrc + "종으로 안 나뉩니다.");
	}
	const target = total / nSrc;

	for (let attempt = 0; attempt < maxTries; attempt++) {
		const left = new Map(codes.map((c) => [c, target]));
		const quota = new Map(codes.map((c) => [c, new Map()]));
		let ok = true;

		for (const pos of positions) {
			const base = Math.floor(slots.get(pos) / nSrc);
			const rem = slots.get(pos) % nSrc;
			const order = codes.slice().sort((a, b) => {
				const d = (left.get(b) - base) - (left.get(a) - base);
				return d !== 0 ? d : rng.random() - 0.5;
			});
			const extra = new Set(order.slice(0, rem));
			for (const c of codes) {
				const q = base + (extra.has(c) ? 1 : 0);
				quota.get(c).set(pos, q);
				left.set(c, left.get(c) - q);
				if (left.get(c) < 0) ok = false;
			}
		}
		if (!ok || [...left.values()].some((v) => v !== 0)) continue;

		const assignment = new Map();
		let good = true;
		for (const pos of positions) {
			const bag = [];
			for (const c of codes) {
				for (let i = 0; i < quota.get(c).get(pos); i++) bag.push(c);
			}
			const placed = dealRoundRobin(byPos.get(pos), bag, reps, rng);
			if (placed === null) { good = false; break; }
			for (const [k, v] of placed) assignment.set(k, v);
		}
		if (good) return assignment;
	}
	throw new Error("정보원 배정 조건을 만족하는 조합을 찾지 못했습니다.");
}

// ── 시행 만들기 ──────────────────────────────────────────

/** 연속 제약과 반복 간격을 만족하는 순서로 늘어놓는다. */
export function orderTrials(cfg, trials, rng, maxTries = 20000) {
	let best = null;
	for (let i = 0; i < maxTries; i++) {
		const seq = rng.shuffle(trials.slice());
		if (!maxRunOk(seq.map((t) => t.sourceCode), cfg.max_run)) continue;
		if (!maxRunOk(seq.map((t) => t.categoryCode), cfg.max_run)) continue;
		if (cfg.max_run_major &&
			!maxRunOk(seq.map((t) => t.majorClass), cfg.max_run_major)) continue;
		if (!repeatLagOk(seq.map((t) => t.setKey), cfg.min_repeat_lag)) {
			best = seq;                      // 반복 간격만 못 맞춘 경우
			continue;
		}
		return seq;
	}
	if (best) return best;
	throw new Error("시행 순서 제약을 만족하는 배열을 찾지 못했습니다.");
}

function makeTrial(cs, recPos, extra, label, code, rep, block) {
	const recType = cs.detailTypes[recPos - 1];
	return {
		block: block,
		setKey: cs.setKey,
		categoryCode: cs.categoryCode,
		categoryKr: cs.categoryKr,
		majorClass: cs.majorClass,
		setId: cs.setId,
		sourceCode: code,
		sourceLabel: label,
		repetition: rep,
		price: cs.price,
		recPosition: recPos,
		recBrand: cs.brands[recPos - 1],
		recDetail: cs.details[recPos - 1],
		recDetailType: recType,
		brands: cs.brands.slice(),
		details: cs.details.slice(),
		detailTypes: cs.detailTypes.slice(),
		extra: extra.slice(),
		phase2: cs.phase2 ? cs.phase2[recType] : "",
	};
}

export function buildTrials(cfg, mainSets, practiceSets, sources, rng) {
	const recPositions = assignRecPositions(cfg, mainSets.map((cs) => cs.setKey), rng);
	const assignment = assignSources(cfg, recPositions, sources.map((s) => s.code), rng);
	const labelOf = new Map(sources.map((s) => [s.code, s.label]));
	const byKey = new Map(mainSets.map((cs) => [cs.setKey, cs]));

	let main = [];
	for (const [setKey, codes] of assignment) {
		const cs = byKey.get(setKey);
		const pos = recPositions.get(setKey);
		// 같은 세트가 다시 나올 때 화면이 글자 그대로 같아야 한다.
		// 그래서 덧붙는 줄도 세트 단위로 한 번만 뽑는다.
		const ex = cfg.n_extra_details ? extraLines(cfg, cs, rng) : [];
		codes.forEach((code, i) => {
			main.push(makeTrial(cs, pos, ex, labelOf.get(code), code, i + 1, "main"));
		});
	}
	main = orderTrials(cfg, main, rng);

	const pool = rng.shuffle(practiceSets.slice());
	const practice = pool.slice(0, cfg.n_practice).map((cs) => {
		const pos = rng.randint(1, cfg.candidates_per_set);
		const ex = cfg.n_extra_details ? extraLines(cfg, cs, rng) : [];
		return makeTrial(cs, pos, ex, cfg.practice_label, "practice", 1, "practice");
	});

	return { practice, trials: main };
}

/** 참가자 ID 하나로 연습과 본 시행을 통째로 뽑는다. */
export function buildDesign(cfg, stim, seedText) {
	const rng = makeRng(seedText);
	const allSets = buildSets(cfg, stim, rng);
	const mainSets = allSets.filter((cs) => cs.block === "main");
	const practiceSets = allSets.filter((cs) => cs.block === "practice");
	if (!practiceSets.length) throw new Error("연습에 쓸 제품군이 없습니다.");
	return buildTrials(cfg, mainSets, practiceSets, stim.sources, rng);
}
