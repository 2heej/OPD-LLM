// 신경과 재진 외래 AI 문진 — UI 프로토타입
//
// 이 스크립트는 서버나 LLM을 호출하지 않는다. 사용자가 입력/선택한 내용을
// NLP_LLM_Prompt_Evaluation.ipynb에서 프롬프트 입력으로 쓰는 것과 같은 형태의
// JSON으로 미리보기만 만든다. 실제 구조화 요약(visit_purpose 등 9개 필드)은
// 노트북에서 LLM이 생성하며, 이 화면은 그 입력값을 만드는 단계까지만 담당한다.

const form = document.getElementById("intake-form");
const symptomSection = document.getElementById("symptom-section");
const symptomDetail = document.getElementById("symptom-detail");
const documentSection = document.getElementById("document-section");
const previewCard = document.getElementById("preview-card");
const previewOutput = document.getElementById("preview-output");

function getCheckedValues(name) {
  return Array.from(form.querySelectorAll(`input[name="${name}"]:checked`)).map(
    (input) => input.value
  );
}

function getRadioValue(name) {
  const checked = form.querySelector(`input[name="${name}"]:checked`);
  return checked ? checked.value : null;
}

// 진료 목적 선택에 따라 조건부 질문 섹션을 보여준다.
function updateConditionalSections() {
  const purposes = getCheckedValues("visit_purpose");

  // 증상 변화(선택형)는 약 처방만 받으러 와도 확인한다. 재진에서 "변화 없음" 확인 자체가 기록 가치가 있다.
  const needsSymptomSection = purposes.includes("증상 상담") || purposes.includes("약 처방");
  symptomSection.hidden = !needsSymptomSection;

  // 서술형 입력(상담 내용, 원문)은 증상 상담을 선택한 경우에만 노출해 입력 부담을 줄인다.
  const consultSelected = purposes.includes("증상 상담");
  symptomDetail.hidden = !consultSelected;

  const needsDocumentSection = purposes.includes("서류 발급");
  documentSection.hidden = !needsDocumentSection;
}

form
  .querySelectorAll('input[name="visit_purpose"]')
  .forEach((checkbox) => checkbox.addEventListener("change", updateConditionalSections));

function buildVisitTypeFields(visitTypeValue) {
  if (visitTypeValue === "guardian_only") {
    return { patient_present: false, guardian_only: true, visit_type_label: "보호자만 방문" };
  }
  if (visitTypeValue === "both") {
    return { patient_present: true, guardian_only: false, visit_type_label: "환자와 보호자가 함께 방문" };
  }
  return { patient_present: true, guardian_only: false, visit_type_label: "환자 본인이 방문" };
}

form.addEventListener("submit", (event) => {
  event.preventDefault();

  const purposes = getCheckedValues("visit_purpose");
  const showsSymptom = !symptomSection.hidden;
  const showsDetail = !symptomDetail.hidden;
  const showsDocument = !documentSection.hidden;
  const visitTypeFields = buildVisitTypeFields(getRadioValue("visit_type"));

  const rawInputParts = [];
  if (showsDetail) {
    const rawText = form.querySelector('textarea[name="subjective_summary_raw"]').value.trim();
    if (rawText) rawInputParts.push(rawText);
  }

  const preview = {
    disease_context: getRadioValue("disease_context"),
    visit_purpose: purposes,
    symptom_change: showsSymptom ? getRadioValue("symptom_change") : null,
    document_type: showsDocument ? getCheckedValues("document_type") : [],
    document_destination: showsDocument ? getCheckedValues("document_destination") : [],
    patient_present: visitTypeFields.patient_present,
    guardian_only: visitTypeFields.guardian_only,
    requested_consultation: showsDetail
      ? form.querySelector('textarea[name="requested_consultation"]').value.trim() || null
      : null,
    raw_input_text: rawInputParts.join(" ") || null,
    _note:
      "subjective_summary, soap_summary는 이 화면에서 만들지 않습니다. raw_input_text를 " +
      "NLP_LLM_Prompt_Evaluation.ipynb의 프롬프트(prompts.py)에 넣으면 LLM이 생성합니다.",
  };

  previewOutput.textContent = JSON.stringify(preview, null, 2);
  previewCard.hidden = false;
  previewCard.scrollIntoView({ behavior: "smooth", block: "start" });
});

updateConditionalSections();
