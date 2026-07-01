# OPD-LLM
# 신경과 재진 외래 AI 문진 — Jupyter 실험 + Flask 데모

## 목적

현재 주 작업물은 [NLP_LLM_Prompt_Evaluation.ipynb](/Users/mac/Documents/Codex/2026-06-22/new-chat/outputs/outpatient-ai-lab/NLP_LLM_Prompt_Evaluation.ipynb)입니다. 코랩·캐글과 같은 셀 실행 방식으로 합성 사례, 프롬프트 v0~v3, 평가 지표와 오류 분석을 확인합니다.

Flask는 LLM 구조화 결과가 외래 문진 화면과 SOAP 초안에 어떻게 적용되는지 보여주는 데모로 유지합니다.

기본 실행 방향은 LLM 기반 요약입니다. OpenAI API 키가 있으면 LLM 요약을 우선 사용하고, API 키가 없거나 호출에 실패하면 앱이 멈추지 않도록 규칙 기반 요약으로 대체됩니다.

## 파일 구성

| 파일·폴더 | 역할 |
|---|---|
| `NLP_LLM_Prompt_Evaluation.ipynb` | 주 실험 노트북 |
| `eval_cases.json` | 비식별 합성 사례와 정답 |
| `prompts.py` | 프롬프트 v0~v3 |
| `app.py` | Flask 데모 서버 |
| `templates/` | 입력·결과 화면 |
| `static/` | 화면 디자인 |
| `requirements.txt` | 필요한 Python 패키지 |
| `.env.example` | API 키 설정 예시 |

## 실행 방법

### 1. Jupyter Notebook 실행

```bash
cd /Users/mac/Documents/Codex/2026-06-22/new-chat/outputs/outpatient-ai-lab
source .venv/bin/activate
pip install -r requirements.txt
jupyter lab
```

브라우저의 Jupyter 화면에서 `NLP_LLM_Prompt_Evaluation.ipynb`를 선택합니다. 위에서부터 셀을 한 개씩 실행합니다.

노트북 결과 확인 위치:

- 실행 직후: 각 코드 셀 아래
- 버전별 지표: `metrics_table` 셀
- 사례별 오류: `error_table` 셀
- 저장 결과: `notebook_results` 폴더

코랩에서 실행할 때는 다음 세 파일을 코랩에 올립니다.

- `NLP_LLM_Prompt_Evaluation.ipynb`
- `eval_cases.json`
- `prompts.py`

노트북의 `코랩에서만 실행합니다` 셀에서 `eval_cases.json`과 `prompts.py`를 선택하면 됩니다.

### 2. Flask 데모 실행

```bash
cd /Users/mac/Documents/Codex/2026-06-22/new-chat/outputs/outpatient-ai-lab
source .venv/bin/activate
python app.py
```

브라우저에서 아래 주소를 엽니다.

```text
http://127.0.0.1:5000
```

## LLM 요약 사용 방법

1. `.env.example`을 복사해서 `.env` 파일을 만듭니다.
2. `.env` 파일의 `OPENAI_API_KEY`에 본인 API 키를 입력합니다.
3. 서버를 다시 실행합니다.

```bash
cp .env.example .env
```

`.env` 예시:

```text
OPENAI_API_KEY=여기에_API_키를_넣으세요
OPENAI_MODEL=gpt-4.1-mini
USE_LLM_SUMMARY=true
```

LLM을 잠시 끄고 규칙 기반 결과만 보고 싶으면 아래처럼 바꿉니다.

```text
USE_LLM_SUMMARY=false
```

## 먼저 만질 파일

처음에는 `NLP_LLM_Prompt_Evaluation.ipynb`만 위에서부터 실행합니다. 평가 사례는 [eval_cases.json](/Users/mac/Documents/Codex/2026-06-22/new-chat/outputs/outpatient-ai-lab/eval_cases.json), 프롬프트 버전은 [prompts.py](/Users/mac/Documents/Codex/2026-06-22/new-chat/outputs/outpatient-ai-lab/prompts.py)에서 수정합니다. 파일을 수정한 뒤 노트북의 `사례와 프롬프트 불러오기` 셀부터 다시 실행합니다.

우선순위:

1. 노트북 환경 설정과 API 키 셀 실행
2. `eval_cases.json`에서 개발 사례와 정답 검토
3. v0 사례 1개 smoke test
4. 개발 세트 v0~v3 평가
5. 오류 분석과 프롬프트 수정
6. 선정된 프롬프트의 시험 세트 평가
7. Flask 데모 화면 확인

## 코랩/캐글 감각으로 이해하기

| 코랩/캐글 작업 | 현재 프로젝트에서 대응되는 부분 |
|---|---|
| 평가 사례와 정답 만들기 | `eval_cases.json` |
| 프롬프트 버전 수정 | `prompts.py` |
| 셀 단위 실행 | `NLP_LLM_Prompt_Evaluation.ipynb` |
| 버전별 점수 비교 | 노트북의 `metrics_table` |
| 오류 사례 확인 | 노트북의 `error_table` |
| 결과 저장 | `notebook_results/` |
| 적용 화면 확인 | Flask 데모 |

## 현재 제외한 것

- 실제 환자 개인정보
- 실제 EMR 연동
- 실제 대기시간 예측
- 실제 진단/처방
- 실제 응급도 판단
- JavaScript 기반 동적 화면

## 다음 단계

노트북에서 개발 세트 결과와 오류를 확인한 뒤 프롬프트를 수정합니다. 최종 프롬프트 하나를 시험 세트에서 평가하고, 측정값과 대표 오류를 포트폴리오에 기록합니다.
