// 두 판의 상수. 파이썬 쪽 CFG와 같은 숫자를 쓴다.
// 숫자를 고치면 파이썬판도 같이 고쳐야 두 판이 안 갈라진다.

const BASE = {
	// 시행 타이밍 (초)
	info_dur: 7.5,            // 정보 국면 자극을 띄워 두는 시간
	decision_dur: 6.0,        // 결정 국면 자극을 띄워 두는 시간
	fix_min: 0.5,             // 고정점 지터 범위
	fix_max: 1.5,
	response_timeout: 12.0,   // 무응답 상한. 넘기면 결측으로 남기고 넘어간다
	feedback_flash: 0.25,     // 확정 뒤 선택 표시를 남겨 두는 시간
	intro_fix_dur: 2.0,       // 과제 시작 직전 고정점

	// 설계
	candidates_per_set: 3,    // 정보 국면에 늘어놓는 후보 수
	repeats_per_set: 2,       // 같은 세트를 몇 번 보여 줄지 (정보원만 바뀜)
	n_practice: 4,
	price_step: 1000,

	// 무작위화 제약
	max_run: 2,               // 같은 정보원 / 같은 제품군 최대 연속 횟수
	max_run_major: 0,         // 0이면 대분류 연속은 안 본다
	min_repeat_lag: 6,        // 같은 세트가 다시 나오기까지 최소 간격

	// 색
	bg_color: "black",
	text_color: "white",
	dim_color: "#9aa0a6",
	label_color: "yellow",    // 정보원 라벨. 본문과 확실히 갈라 놓는다
	accent_color: "red",      // 선택된 리커트 원
	warn_color: "yellow",

	// 글자
	font: "Malgun Gothic, NanumGothic, Noto Sans KR, sans-serif",
	h_label: 0.085,
	h_brand: 0.046,
	h_feature: 0.038,
	h_price: 0.05,
	h_detail: 0.034,
	h_question: 0.042,
	h_number: 0.034,
	h_anchor: 0.028,
	h_instruction: 0.038,

	// 화면 배치
	label_y: 0.4,
	candidates_top: 0.24,
	candidate_gap: 0.1,
	brand_y: 0.25,
	price_y: 0.17,
	detail_top: 0.06,
	detail_gap: 0.055,

	// 리커트 7점
	scale_n: 7,
	circle_radius: 0.038,
	circle_line_width: 3.0,
	question_y: -0.15,
	scale_y: -0.26,
	numbers_y: -0.335,
	desc_y: -0.395,
	scale_x_left: -0.36,
	scale_x_right: 0.36,

	// 이분 선택
	binary_x: 0.27,
	binary_y: -0.26,
	binary_box_w: 0.4,
	binary_box_h: 0.1,

	practice_label: "[예시 정보원]",
};

export const TXT = {
	welcome:
		"이 과제에서는 여러 제품 중 하나를 정보원이 골라 알려 줍니다.\n\n" +
		"화면 맨 위에 어떤 정보원인지 나옵니다.\n" +
		"제품을 살펴본 뒤 물음에 답해 주세요.\n\n" +
		"계속하려면 스페이스바를 누르세요.",
	keys:
		"응답 방법\n\n" +
		"  ←  →      선택을 옮깁니다\n" +
		"  Enter     선택을 확정합니다\n\n" +
		"한 번 확정하면 되돌릴 수 없습니다.\n" +
		"확정하기 전에 화면을 확인해 주세요.\n\n" +
		"계속하려면 스페이스바를 누르세요.",
	practice:
		"먼저 연습을 네 번 하겠습니다.\n\n" +
		"연습에 나오는 제품은 본 과제에 나오지 않습니다.\n\n" +
		"계속하려면 스페이스바를 누르세요.",
	taskStart:
		"연습이 끝났습니다.\n\n" +
		"지금부터 본 과제입니다. 약 15분 걸립니다.\n" +
		"중간에 쉬는 구간이 한 번 있습니다.\n\n" +
		"계속하려면 스페이스바를 누르세요.",
	breakText: "잠시 쉬어 가겠습니다.\n\n준비가 되면 스페이스바를 눌러 주세요.",
	end: "과제가 끝났습니다.\n\n이어서 사후 설문을 진행합니다.\n연구자에게 알려 주세요.",
	paused: "일시 정지\n\n계속하려면  N\n종료하려면  Y",
};

export const Q = {
	info: "이 중에 구매할 만한 게 있어 보입니까?",
	infoLeft: "전혀 없어 보인다",
	infoRight: "매우 있어 보인다",
	binary: "이 제품을 구매하시겠습니까?",
	optBuy: "구매한다",
	optNoBuy: "구매하지 않는다",
	intent: "이 제품을 얼마나 구매하고 싶습니까?",
	intentLeft: "전혀 그렇지 않다",
	intentRight: "매우 그렇다",
};

export const VARIANTS = {
	classic: Object.assign({}, BASE, {
		title: "기존판 · 제품군 8개",
		exp_name: "GPTC_task_web",
		stim_key: "classic",
		sets_per_category: 3,
		n_extra_details: 2,       // 결정 국면에서 특징 아래 붙는 줄 수
	}),
	list0818: Object.assign({}, BASE, {
		title: "0818 리스트판 · 제품군 21개",
		exp_name: "GPTC_task_0818_web",
		stim_key: "list0818",
		sets_per_category: 1,
		n_extra_details: 0,       // 대신 phase2 문장 한 줄
		max_run_major: 2,
	}),
};
