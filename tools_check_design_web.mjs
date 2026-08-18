// 웹판 설계 검사기. tools_check_design.py 와 같은 조건을 본다.
//
//     node tools_check_design_web.mjs [반복수]
//
// 파이썬 검사기가 GPTC_task.py 를 보는 것처럼, 이쪽은 web/gptc_design.js 와
// web/gptc_config.js 를 본다. psychojs는 안 띄운다.

import { STIM } from "./web/gptc_stim.js";
import { VARIANTS } from "./web/gptc_config.js";
import { buildDesign, buildSets, makeRng } from "./web/gptc_design.js";

const N = Number(process.argv[2] || 200);
const fails = [];
const check = (cond, msg) => { if (!cond) fails.push(msg); };

function maxRun(seq) {
	let best = 1, run = 1;
	for (let i = 1; i < seq.length; i++) {
		run = seq[i] === seq[i - 1] ? run + 1 : 1;
		if (run > best) best = run;
	}
	return best;
}

function counter(arr) {
	const m = new Map();
	for (const v of arr) m.set(v, (m.get(v) || 0) + 1);
	return m;
}

function runOne(cfg, stim, seed) {
	const { practice, trials } = buildDesign(cfg, stim, seed);
	const mainCats = stim.categories.filter((c) => c.block === "main");
	const expected = mainCats.length * cfg.sets_per_category * cfg.repeats_per_set;

	check(trials.length === expected, `시행 수 ${trials.length} != ${expected}`);
	check(practice.length === cfg.n_practice,
		`연습 시행 ${practice.length} != ${cfg.n_practice}`);
	const mainCodes = new Set(mainCats.map((c) => c.code));
	check(!practice.some((t) => mainCodes.has(t.categoryCode)),
		"연습에 본 과제 제품군이 섞임");

	// 정보원별 균형
	const perSource = counter(trials.map((t) => t.sourceCode));
	check(perSource.size === stim.sources.length, "안 쓰인 정보원이 있음");
	check(new Set(perSource.values()).size === 1,
		"정보원별 시행 수가 고르지 않음: " + JSON.stringify([...perSource]));

	const posBySource = new Map();
	for (const t of trials) {
		if (!posBySource.has(t.sourceCode)) posBySource.set(t.sourceCode, []);
		posBySource.get(t.sourceCode).push(t.recPosition);
	}
	for (const [code, poss] of posBySource) {
		const c = counter(poss);
		const spread = Math.max(...c.values()) - Math.min(...c.values());
		check(c.size === cfg.candidates_per_set && spread <= 1,
			`${code} 추천 위치가 고르지 않음: ` + JSON.stringify([...c]));
	}

	// 세트별 조건
	const bySet = new Map();
	for (const t of trials) {
		if (!bySet.has(t.setKey)) bySet.set(t.setKey, []);
		bySet.get(t.setKey).push(t);
	}
	for (const [key, group] of bySet) {
		check(group.length === cfg.repeats_per_set, `${key} 등장 횟수 ${group.length}`);
		check(new Set(group.map((t) => t.sourceCode)).size === group.length,
			`${key} 같은 정보원이 두 번`);
		const first = group[0];
		for (const t of group.slice(1)) {
			for (const f of ["recBrand", "recPosition", "price", "phase2"]) {
				check(String(t[f]) === String(first[f]), `${key} ${f}가 다름`);
			}
			for (const f of ["brands", "details", "extra"]) {
				check(t[f].join("|") === first[f].join("|"), `${key} ${f}가 다름`);
			}
		}
	}

	// 세트 안 구성
	const rng = makeRng(seed);
	const allSets = buildSets(cfg, stim, rng);
	const byCode = new Map(stim.categories.map((c) => [c.code, c]));
	const allBrands = [];
	for (const cs of allSets) {
		check(new Set(cs.brands).size === cs.brands.length, `${cs.setKey} 브랜드 중복`);
		check(new Set(cs.details).size === cs.details.length, `${cs.setKey} 특징 중복`);
		const cat = byCode.get(cs.categoryCode);
		check(cs.price >= cat.low && cs.price <= cat.high,
			`${cs.setKey} 가격 ${cs.price}이 범위 밖`);
		allBrands.push(...cs.brands);
	}
	check(new Set(allBrands).size === allBrands.length, "참가자 안에서 브랜드명 중복");

	// 결정 국면 문구
	for (const t of trials.concat(practice)) {
		if (cfg.n_extra_details) {
			const lines = [t.recDetail, ...t.extra];
			check(new Set(lines).size === lines.length, `${t.setKey} 결정 국면 문구 중복`);
		} else {
			check(t.phase2 === stim.phase2[t.categoryCode][t.recDetailType],
				`${t.setKey} 결정 국면 문장이 추천 문구 유형과 안 맞음`);
		}
	}

	// 연속 제약
	check(maxRun(trials.map((t) => t.sourceCode)) <= cfg.max_run, "같은 정보원 연속 초과");
	check(maxRun(trials.map((t) => t.categoryCode)) <= cfg.max_run, "같은 제품군 연속 초과");
	if (cfg.max_run_major) {
		check(maxRun(trials.map((t) => t.majorClass)) <= cfg.max_run_major,
			"같은 대분류 연속 초과");
	}

	let last = new Map(), minLag = 99;
	trials.forEach((t, i) => {
		if (last.has(t.setKey)) minLag = Math.min(minLag, i - last.get(t.setKey));
		last.set(t.setKey, i);
	});
	return minLag;
}

let bad = 0;
for (const [name, cfg] of Object.entries(VARIANTS)) {
	const stim = STIM[cfg.stim_key];
	const before = fails.length;
	const mainCats = stim.categories.filter((c) => c.block === "main");
	const prac = stim.categories.filter((c) => c.block === "practice");
	const expected = mainCats.length * cfg.sets_per_category * cfg.repeats_per_set;

	console.log(`\n── ${name} (${cfg.title}) ──`);
	console.log(`정보원 ${stim.sources.length}종, 본 과제 제품군 ${mainCats.length}개, ` +
		`연습 전용 ${prac.length}개 (${prac.map((c) => c.kr).join(", ")})`);
	console.log(`예상 시행 : ${mainCats.length} x ${cfg.sets_per_category}세트 x ` +
		`${cfg.repeats_per_set}회 = ${expected}시행, ` +
		`정보원당 ${(expected / stim.sources.length).toFixed(1)}`);
	check(expected % stim.sources.length === 0, `${name}: 시행 수가 정보원 수로 안 나뉨`);

	const lags = [];
	for (let s = 0; s < N; s++) lags.push(runOne(cfg, stim, "seed" + s));
	lags.sort((a, b) => a - b);
	console.log(`가상 참가자 ${N}명 배치 생성 완료`);
	console.log(`같은 세트 재등장 최소 간격: 중앙값 ${lags[lags.length >> 1]}, 최소 ${lags[0]}`);

	const mine = fails.slice(before);
	if (mine.length) {
		bad = 1;
		console.log(`\n실패 ${mine.length}건`);
		[...new Set(mine)].slice(0, 10).forEach((m) => console.log("  x", m));
	} else {
		console.log("모든 조건 통과");
	}
}
process.exit(bad);
