# 고칠 때

## 자극 문구를 바꾸려면

`stim/` 아래 CSV를 고친다. 코드는 건드리지 않는다.

- `categories.csv` 제품군, 섹터, 가격 범위
- `details.csv` 제품군마다의 특징 (실용 3 + 감성 3)
- `sources.csv` 정보원 6종

고친 뒤에는 두 개를 돌려 본다.

```
python tools_check_design.py 300   설계 제약이 여전히 지켜지는지
python tools_preview.py 7          화면 문구가 넘치지 않는지
python tools_make_xlsx.py          엑셀 사본 갱신
```

## 시행 수를 바꾸려면

`GPTC_task.py` 맨 위 `CFG`의 숫자를 고친다.

```
시행 수 = (제품군 수 - 제외 수) x 세트 수 x 반복 수
```

정보원 수로 나눠떨어져야 한다. 안 떨어지면 `tools_check_design.py`가 잡아 준다.

## 화면을 바꾸려면

`GPTC_task.py`의 `info_stims`, `decision_stims`, `header`를 본다. 좌표와 글자
크기는 전부 `CFG`에 있다.

바꾼 뒤에는 창 모드로 눈으로 확인한다.

```
python GPTC_task.py --windowed
python GPTC_task.py --record 확인용    자동 진행을 4배속 영상으로
```
