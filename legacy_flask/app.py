"""
신경과 재진 외래 AI 문진 Lab — Flask 시제품 (참고용, 현재 범위 밖)

이 프로젝트의 핵심 산출물은 NLP_LLM_Prompt_Evaluation.ipynb(프롬프트 평가)와
frontend/(문진 UI 프로토타입)이며, 이 Flask 앱은 그 산출물을 실제 서비스로
연결할 때 후보가 될 수 있는 백엔드 예시로만 legacy_flask/에 보관합니다.
현재 개발·평가 대상이 아니므로 유지보수하지 않습니다.

핵심 목적(과거):
- 실제 환자용 demo 이전에 입력 구조, 증상 분류 규칙, 위험 표현 감지, SOAP 초안 형식을 검증한다.
- 실제 환자 개인정보는 사용하지 않고, 비식별·합성 문장만 입력한다.

과거 구현:
- Flask + HTML 템플릿
- LLM 우선 구조화 요약
- API 키 없음 또는 LLM 호출 실패 시 Python 규칙 기반 요약으로 대체
- 위험 표현 감지
- 의료진 검토용 SOAP 초안
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import Literal

from flask import Flask, render_template, request

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


app = Flask(__name__)


# =============================================================================
# 1. 사용자가 직접 튜닝할 영역
# =============================================================================
# 코랩/캐글에서 데이터와 전처리 규칙을 바꿔보던 것처럼,
# 우선 이 상수와 함수만 수정하면 됩니다.

DEMO_CASES = [
    {
        "id": "case-1",
        "label": "검증 케이스 1",
        "age": 70,
        "department": "신경과",
        "doctor": "박OO 교수",
        "time": "오후 2:30",
        "room": "신경과 3번 진료실",
        "tests_ready": "마지막 진료 후 시행 검사 없음",
    },
    {
        "id": "case-2",
        "label": "검증 케이스 2",
        "age": 65,
        "department": "신경과",
        "doctor": "최OO 교수",
        "time": "오전 10:20",
        "room": "신경과 5번 진료실",
        "tests_ready": "검사/평가 결과 확인 가능",
    },
    {
        "id": "case-3",
        "label": "검증 케이스 3",
        "age": 50,
        "department": "신경과",
        "doctor": "한OO 교수",
        "time": "오후 4:00",
        "room": "신경과 2번 진료실",
        "tests_ready": "검사/평가 결과 확인 가능",
    },
]

PURPOSE_OPTIONS = ["약 처방", "증상 상담", "서류 발급", "검사결과 확인"]
SYMPTOM_CHANGE_OPTIONS = ["좋아짐", "비슷함", "나빠짐", "새 증상 있음", "잘 모르겠음"]
DOCUMENT_OPTIONS = ["진단서", "소견서", "통원사실증명서(진료확인서)", "기록/결과 사본", "개인 양식", "기타/종류 모름"]
DESTINATION_OPTIONS = ["보험", "직장/학교", "공공기관", "타 의료기관", "개인 보관", "제출처 모름"]
VISIT_TYPE_OPTIONS = ["환자 본인이 방문", "환자와 보호자가 함께 방문", "보호자만 방문"]

# 실제 LLM 호출에 우선 적용되는 요약 지침입니다.
# OPENAI_API_KEY가 있으면 실제 LLM 호출에 사용되고,
# 없으면 규칙 기반 요약의 지침 문구로 표시됩니다.
SUMMARY_INSTRUCTION = "너는 의사의 진료 보조를 돕는 의료 코디네이터야. 의료진 확인용으로 내용을 요약하되, 확실하지 않으면 환자의 말을 그대로 출력해줘."

# LLM 연결 설정입니다. 기본값은 LLM 사용입니다.
# .env 파일 또는 터미널 환경변수에서 값을 바꿀 수 있습니다.
USE_LLM_SUMMARY = os.getenv("USE_LLM_SUMMARY", "true").lower() == "true"
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")


# 위험 표현 감지용 키워드입니다.
# 실제 응급도 판단이 아니라 "직원 확인 권장" 표시용입니다.
RISK_KEYWORDS = [
    "한쪽 힘",
    "힘이 빠",
    "마비",
    "말이 어눌",
    "말이 안",
    "심한 두통",
    "머리를 부딪",
    "넘어졌",
    "낙상",
    "발작이 5분",
    "반복 발작",
    "숨을 못",
    "호흡",
    "의식",
    "실신",
    "삼키기",
    "사레",
]

# 신경과 표현 분류 규칙입니다.
# 왼쪽은 요약에 표시될 라벨, 오른쪽은 감지할 표현입니다.
NEURO_PATTERNS = {
    "기억/인지 변화": r"기억|깜빡|인지|길을 잃|반복|계산|이름|날짜|헷갈",
    "행동/정신증상": r"환시|망상|불안|우울|공격|배회|잠을 안|성격|밤에",
    "운동/보행 변화": r"떨|진전|느려|느림|굳|경직|뻣뻣|걷|걸음|균형|넘어|낙상|비틀|얼어",
    "에피소드/의식 변화": r"발작|경련|멍해|의식|쓰러|실신|대답 못|기억이 안",
    "감각/통증 변화": r"저림|감각|화끈|시림|찌릿|통증|아프|쑤시",
    "약 관련 변화": r"약|복용|처방|중단|빼먹|누락|부작용|약효",
}


# =============================================================================
# 2. 데이터 구조
# =============================================================================


@dataclass
class IntakeInput:
    case_id: str
    disease_context: str
    case_memo: str
    purposes: list[str]
    symptom_change: str
    symptom_text: str
    documents: list[str]
    destinations: list[str]
    visit_type: str
    safety_items: list[str]


@dataclass
class StructuredSummary:
    source: str
    instruction: str
    disease_context: str
    symptom_change: str
    main_symptoms: list[str]
    onset: str
    aggravating_factors: list[str]
    medication_mention: str
    core_change: str
    daily_function: str
    patient_concern: str
    clinician_check_items: list[str]


@dataclass
class SoapDraft:
    subjective: list[str] = field(default_factory=list)
    objective: list[str] = field(default_factory=list)
    assessment_checklist: list[str] = field(default_factory=list)
    plan_agenda: list[str] = field(default_factory=list)


# =============================================================================
# 3. 구조화 요약
# =============================================================================


def selected_case(case_id: str) -> dict:
    return next((case for case in DEMO_CASES if case["id"] == case_id), DEMO_CASES[0])


def detect_risk(text: str) -> bool:
    return any(keyword in text for keyword in RISK_KEYWORDS)


def infer_onset(text: str) -> str:
    match = re.search(r"(오늘|어제|그제|지난주|이번주|한 달|최근|\d+일 전|\d+주 전|\d+개월 전|며칠 전|몇 주 전)", text)
    return match.group(0) if match else "확인 필요"


def split_checked_values(name: str) -> list[str]:
    return request.form.getlist(name)


def structure_neurology_text(text: str, symptom_change: str, disease_context: str) -> StructuredSummary:
    """LLM을 사용할 수 없을 때 적용하는 규칙 기반 대체 요약 함수입니다."""
    main_symptoms: list[str] = []
    aggravating_factors: list[str] = []
    clinician_checks: list[str] = []

    for label, pattern in NEURO_PATTERNS.items():
        if re.search(pattern, text):
            main_symptoms.append(label)

    if re.search(r"약효|시간|다음 약", text):
        aggravating_factors.append("약효 시간과 관련된 변동 가능성")
    if re.search(r"밤|수면|새벽", text):
        aggravating_factors.append("수면 또는 야간 증상 관련")
    if re.search(r"계단|걷|걸음|외출", text):
        aggravating_factors.append("보행 또는 활동 상황 관련")

    if re.search(r"약|복용|처방|중단|빼먹|누락|부작용|약효", text):
        medication_mention = "약 관련 언급 있음"
        clinician_checks.append("복약 여부와 약효/부작용 확인")
    else:
        medication_mention = "약 관련 언급 없음"

    if re.search(r"낙상|넘어|머리를 부딪", text):
        clinician_checks.append("낙상 및 외상 여부 확인")
    if re.search(r"발작|경련|멍해|의식|대답 못", text):
        clinician_checks.append("에피소드 양상, 지속 시간, 회복 여부 확인")
    if re.search(r"반복|기억|배회|보호자|생활", text):
        clinician_checks.append("인지·행동 변화와 일상생활 영향 확인")
    if re.search(r"걸|굳|느려|떨|동결", text):
        clinician_checks.append("운동 증상 변동과 보행 영향 확인")
    if symptom_change in ["나빠짐", "새 증상 있음"]:
        clinician_checks.append("변화 시작 시점과 진행 양상 확인")
    if detect_risk(text):
        clinician_checks.insert(0, "위험 표현 감지: 직원 확인 권장")

    return StructuredSummary(
        source="규칙 기반 요약",
        instruction=SUMMARY_INSTRUCTION,
        disease_context=disease_context or "신경과 재진",
        symptom_change=symptom_change or "확인 필요",
        main_symptoms=main_symptoms or ["환자 표현 기반 확인 필요"],
        onset=infer_onset(text),
        aggravating_factors=aggravating_factors or ["확인 필요"],
        medication_mention=medication_mention,
        core_change=build_core_change(text, disease_context),
        daily_function="일상생활 영향 확인 필요" if re.search(r"생활|보호자|복약|식사|옷|씻|운전|낙상|넘어", text) else "확인 필요",
        patient_concern=text or "추가 설명 없음",
        clinician_check_items=clinician_checks or ["환자가 말한 내용을 진료 중 확인"],
    )


def summarize_with_llm(text: str, symptom_change: str, disease_context: str) -> StructuredSummary | None:
    """OpenAI API가 설정되어 있으면 우선 LLM으로 구조화 요약을 생성합니다.

    실패하면 None을 반환하고, 호출부에서 규칙 기반 요약으로 대체합니다.
    """
    if not USE_LLM_SUMMARY or not os.getenv("OPENAI_API_KEY"):
        return None

    try:
        from openai import OpenAI

        client = OpenAI()
        response = client.responses.create(
            model=OPENAI_MODEL,
            instructions=(
                f"{SUMMARY_INSTRUCTION}\n"
                "외래 진료 전 문진 요약을 만든다.\n"
                "진단명, 처방, 치료 계획은 생성하지 않는다.\n"
                "입력에 없는 정보는 추정하지 않는다.\n"
                "불확실하면 '확인 필요'라고 쓰거나 환자 표현을 그대로 남긴다.\n"
                "반드시 JSON만 출력한다."
            ),
            input=(
                "다음 환자 입력을 신경과 재진 외래 문진용으로 구조화해줘.\n\n"
                f"질환군/진료 맥락: {disease_context or '신경과 재진'}\n"
                f"증상 변화 선택: {symptom_change or '선택 없음'}\n"
                f"환자/보호자 입력 원문: {text or '입력 없음'}\n\n"
                "JSON 형식:\n"
                "{\n"
                '  "disease_context": "문자열",\n'
                '  "symptom_change": "문자열",\n'
                '  "main_symptoms": ["문자열"],\n'
                '  "onset": "문자열",\n'
                '  "aggravating_factors": ["문자열"],\n'
                '  "medication_mention": "문자열",\n'
                '  "core_change": "문자열",\n'
                '  "daily_function": "문자열",\n'
                '  "patient_concern": "문자열",\n'
                '  "clinician_check_items": ["문자열"]\n'
                "}"
            ),
        )
        payload = parse_json_object(response.output_text)
        return StructuredSummary(
            source=f"LLM 요약 ({OPENAI_MODEL})",
            instruction=SUMMARY_INSTRUCTION,
            disease_context=str(payload.get("disease_context") or disease_context or "신경과 재진"),
            symptom_change=str(payload.get("symptom_change") or symptom_change or "확인 필요"),
            main_symptoms=as_string_list(payload.get("main_symptoms")) or ["환자 표현 기반 확인 필요"],
            onset=str(payload.get("onset") or infer_onset(text)),
            aggravating_factors=as_string_list(payload.get("aggravating_factors")) or ["확인 필요"],
            medication_mention=str(payload.get("medication_mention") or "확인 필요"),
            core_change=str(payload.get("core_change") or build_core_change(text, disease_context)),
            daily_function=str(payload.get("daily_function") or "확인 필요"),
            patient_concern=str(payload.get("patient_concern") or text or "추가 설명 없음"),
            clinician_check_items=as_string_list(payload.get("clinician_check_items")) or ["환자가 말한 내용을 진료 중 확인"],
        )
    except Exception as error:
        print(f"[LLM fallback] {error}")
        return None


def parse_json_object(raw_text: str) -> dict:
    """LLM 출력에서 JSON 객체만 추출합니다."""
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()
    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if not match:
        raise ValueError("LLM 응답에서 JSON 객체를 찾지 못했습니다.")
    return json.loads(match.group(0))


def as_string_list(value) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def build_core_change(text: str, disease_context: str) -> str:
    matched: list[str] = []
    if re.search(r"기억|반복|배회|환시|망상|성격|생활", text):
        matched.append("인지/행동 변화")
    if re.search(r"떨|굳|느려|걷|걸음|동결|넘어|낙상", text):
        matched.append("운동/보행 변화")
    if re.search(r"발작|경련|멍해|의식|대답 못|기억이 안", text):
        matched.append("에피소드/의식 변화")
    if re.search(r"약|복용|처방|중단|빼먹|누락|부작용|약효", text):
        matched.append("약 관련 변화")
    return ", ".join(matched) if matched else f"{disease_context or '신경과 재진'} 관련 핵심 변화 확인 필요"


def safety_level(safety_items: list[str], free_text: str) -> Literal["none", "recommend", "need"]:
    selected_danger = any(item != "해당 없음" for item in safety_items)
    if selected_danger:
        return "need"
    if detect_risk(free_text):
        return "recommend"
    return "none"


def build_soap(case: dict, intake: IntakeInput, summary: StructuredSummary | None) -> SoapDraft:
    level = safety_level(intake.safety_items, f"{intake.case_memo} {intake.symptom_text}")
    checks: list[str] = []

    if level == "need":
        checks.append("안전 확인 항목 선택됨: 직원 확인 필요")
    elif level == "recommend":
        checks.append("위험 표현 감지: 직원 확인 권장")

    if summary:
        checks.extend(summary.clinician_check_items)
    if intake.documents:
        checks.append(f"서류 요청 확인: {', '.join(intake.documents)} / 제출처: {', '.join(intake.destinations) or '확인 필요'}")
    if intake.visit_type == "보호자만 방문":
        checks.append("보호자 단독 방문: 진료 및 서류 발급 조건 확인 필요")

    subjective = [
        f"오늘 방문 목적: {', '.join(intake.purposes) or '확인 필요'}",
        f"질환군/진료 맥락: {intake.disease_context or '신경과 재진'}",
    ]
    if summary:
        subjective.extend(
            [
                f"요약 방식: {summary.source}",
                f"요약 지침: {summary.instruction}",
                f"증상 변화: {summary.symptom_change}",
                f"주요 증상: {', '.join(summary.main_symptoms)}",
                f"핵심 변화: {summary.core_change}",
                f"일상생활 변화: {summary.daily_function}",
                f"환자 표현 원문: {summary.patient_concern}",
            ]
        )
    else:
        subjective.append("증상 변화 선택 없음")
    subjective.append(f"서류 요청: {', '.join(intake.documents) if intake.documents else '없음'}")
    subjective.append(f"방문 형태: {intake.visit_type or '확인 필요'}")

    objective = [
        f"예약 진료과: {case['department']}",
        f"담당의: {case['doctor']}",
        f"예약 시각: {case['time']}",
        f"검사 상태: {case['tests_ready']}",
        "환자 입력만으로 확인할 수 없는 진찰 소견과 검사값은 생성하지 않음",
    ]

    plan_agenda = [f"{purpose} 관련 진료 의제 확인" for purpose in intake.purposes]
    plan_agenda.append("진단, 처방, 치료 계획은 생성하지 않음")

    return SoapDraft(
        subjective=subjective,
        objective=objective,
        assessment_checklist=checks or ["특이 확인 필요 항목 없음"],
        plan_agenda=plan_agenda,
    )


# =============================================================================
# 4. Flask 라우트
# =============================================================================


@app.get("/")
def index():
    return render_template(
        "index.html",
        cases=DEMO_CASES,
        purpose_options=PURPOSE_OPTIONS,
        symptom_change_options=SYMPTOM_CHANGE_OPTIONS,
        document_options=DOCUMENT_OPTIONS,
        destination_options=DESTINATION_OPTIONS,
        visit_type_options=VISIT_TYPE_OPTIONS,
    )


@app.post("/result")
def result():
    case_id = request.form.get("case_id", DEMO_CASES[0]["id"])
    case = selected_case(case_id)
    symptom_text = request.form.get("symptom_text", "").strip()
    case_memo = request.form.get("case_memo", "").strip()
    symptom_change = request.form.get("symptom_change", "")
    disease_context = request.form.get("disease_context", "").strip()

    intake = IntakeInput(
        case_id=case_id,
        disease_context=disease_context,
        case_memo=case_memo,
        purposes=split_checked_values("purposes"),
        symptom_change=symptom_change,
        symptom_text=symptom_text,
        documents=split_checked_values("documents"),
        destinations=split_checked_values("destinations"),
        visit_type=request.form.get("visit_type", ""),
        safety_items=split_checked_values("safety_items"),
    )

    should_summarize = "증상 변화" in intake.purposes or bool(symptom_text)
    summary_text = symptom_text or case_memo
    summary = summarize_with_llm(summary_text, symptom_change, disease_context) if should_summarize else None
    if should_summarize and summary is None:
        summary = structure_neurology_text(summary_text, symptom_change, disease_context)
    soap = build_soap(case, intake, summary)
    level = safety_level(intake.safety_items, f"{case_memo} {symptom_text}")

    return render_template(
        "result.html",
        case=case,
        intake=intake,
        summary=summary,
        soap=soap,
        safety_level=level,
    )


if __name__ == "__main__":
    app.run(debug=True)
