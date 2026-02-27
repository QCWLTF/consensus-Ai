# -*- coding: utf-8 -*-
"""
Consensus AI: 논문 분석을 위한 다중 AI 교차 검증 프로토타입
- PDF 업로드 또는 텍스트 입력 → 여러 AI가 토의하여 최적의 결과 도출
- 1주차: PDF 업로드 구현 (복사-붙여넣기와의 결별)
- 2주차: 일반 모드 vs 심층 토론 모드 (상호 비판 로직)
"""

import io
import streamlit as st
from openai import OpenAI
from anthropic import Anthropic
from google import genai

# PDF 텍스트 추출 (PyMuPDF)
try:
    import fitz  # PyMuPDF

    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

# =============================================================================
# 지원 AI 목록 및 API 키 발급 링크
# =============================================================================
AI_CONFIG = {
    "openai": {
        "name": "GPT (OpenAI)",
        "key_label": "OpenAI API Key",
        "placeholder": "sk-...",
        "api_url": "https://platform.openai.com/api-keys",
        "model": "gpt-4o",
    },
    "gemini": {
        "name": "Gemini (Google)",
        "key_label": "Google Gemini API Key",
        "placeholder": "AIza...",
        "api_url": "https://aistudio.google.com/app/apikey",
        "model": "gemini-2.0-flash",
    },
    "perplexity": {
        "name": "Perplexity",
        "key_label": "Perplexity API Key",
        "placeholder": "pplx-...",
        "api_url": "https://www.perplexity.ai/account/api/group",
        "model": "sonar-pro",
    },
    "claude": {
        "name": "Claude (Anthropic)",
        "key_label": "Anthropic Claude API Key",
        "placeholder": "sk-ant-...",
        "api_url": "https://console.anthropic.com/",
        "model": "claude-sonnet-4-6",
    },
}


# =============================================================================
# PDF 텍스트 추출 (PyMuPDF - 수식/레이아웃 보존에 유리)
# =============================================================================
def extract_text_from_pdf(uploaded_file) -> str:
    """PDF에서 텍스트 추출. blocks 모드로 레이아웃·수식 표현을 최대한 보존."""
    try:
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        text_parts = []
        for page in doc:
            # blocks 모드: 문단/수식 단위로 구조화된 추출
            blocks = page.get_text("blocks")
            for block in blocks:
                if block[4].strip():
                    text_parts.append(block[4].strip())
        doc.close()
        return "\n\n".join(text_parts) if text_parts else ""
    except Exception as e:
        return f"❌ PDF 추출 오류: {str(e)}"


# =============================================================================
# 각 AI별 응답 호출 함수
# =============================================================================
def call_openai(api_key: str, prompt: str) -> str:
    """OpenAI GPT 호출"""
    client = OpenAI(api_key=api_key)
    completion = client.chat.completions.create(
        model=AI_CONFIG["openai"]["model"],
        messages=[{"role": "user", "content": prompt}],
    )
    return completion.choices[0].message.content


def call_gemini(api_key: str, prompt: str) -> str:
    """Google Gemini 호출"""
    client = genai.Client(api_key=api_key)
    result = client.models.generate_content(
        model=AI_CONFIG["gemini"]["model"],
        contents=prompt,
    )
    return result.text


def call_perplexity(api_key: str, prompt: str) -> str:
    """Perplexity 호출 (OpenAI 호환 API)"""
    client = OpenAI(
        api_key=api_key,
        base_url="https://api.perplexity.ai",
    )
    completion = client.chat.completions.create(
        model=AI_CONFIG["perplexity"]["model"],
        messages=[{"role": "user", "content": prompt}],
    )
    return completion.choices[0].message.content


def call_claude(api_key: str, prompt: str) -> str:
    """Anthropic Claude 호출"""
    client = Anthropic(api_key=api_key)
    message = client.messages.create(
        model=AI_CONFIG["claude"]["model"],
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


CALL_FUNCTIONS = {
    "openai": call_openai,
    "gemini": call_gemini,
    "perplexity": call_perplexity,
    "claude": call_claude,
}


# =============================================================================
# 페이지 설정
# =============================================================================
st.set_page_config(
    page_title="Consensus AI - 논문 분석",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =============================================================================
# 사이드바: API 키, 모드 선택
# =============================================================================
with st.sidebar:
    st.header("🔑 API 키 설정")
    st.caption("보유한 API 키만 입력하세요. 입력한 AI들만 토의에 참여합니다.")
    st.markdown("---")

    api_keys = {}
    for ai_id, config in AI_CONFIG.items():
        st.markdown(f"**{config['name']}**")
        st.link_button(
            "🔗 API 키 발급 바로가기",
            url=config["api_url"],
            type="secondary",
        )
        api_keys[ai_id] = st.text_input(
            config["key_label"],
            key=f"key_{ai_id}",
            type="password",
            placeholder=config["placeholder"],
            label_visibility="collapsed",
        )
        st.markdown("---")

    st.caption("⚠️ API 키는 브라우저에 저장되지 않으며, 세션 동안에만 사용됩니다.")
    st.markdown("---")

    # 2주차: 일반 모드 vs 심층 토론 모드 선택
    st.header("⚙️ 분석 모드")
    analysis_mode = st.radio(
        "모드 선택",
        ["일반 모드 (단순 종합)", "심층 토론 모드 (상호 비판)"],
        help="일반 모드: 각 AI 답변 → 종합. 심층 토론: A 답변 → B가 검토·지적 → A가 수정 후 최종 종합. (토큰 비용 2~3배)",
    )
    is_deep_mode = "심층" in analysis_mode

# 사용 가능한 AI 목록
available_ais = {k: v for k, v in api_keys.items() if v and v.strip()}


# =============================================================================
# 메인 화면: 입력 (PDF 업로드 + 텍스트)
# =============================================================================
st.title("📚 Consensus AI: 논문 분석을 위한 다중 AI 교차 검증")
st.markdown(
    "**PDF를 업로드**하거나 **텍스트를 붙여넣기**하세요. 보유한 AI들이 토의 후 최적의 분석을 제안합니다."
)
st.markdown("---")

if available_ais:
    ai_names = [AI_CONFIG[k]["name"] for k in available_ais]
    st.success(f"✅ 토의 참여 AI: {', '.join(ai_names)} | 모드: {analysis_mode}")
else:
    st.warning("⚠️ 사이드바에서 최소 1개 이상의 API 키를 입력해주세요.")

st.markdown("---")

# 1주차: PDF 업로드 (복사-붙여넣기와의 결별)
extracted_text = ""
if PDF_AVAILABLE:
    st.subheader("📄 논문 입력")
    pdf_file = st.file_uploader(
        "PDF 파일 업로드 (논문을 던지면 텍스트가 자동 추출됩니다)",
        type=["pdf"],
        help="PDF를 업로드하면 PyMuPDF로 텍스트를 추출합니다. 수식·표 구조를 최대한 보존합니다.",
    )
    if pdf_file:
        with st.spinner("PDF에서 텍스트를 추출하고 있습니다..."):
            extracted_text = extract_text_from_pdf(pdf_file)
        if extracted_text and not extracted_text.startswith("❌"):
            st.success(f"✅ PDF 텍스트 추출 완료 ({len(extracted_text):,}자)")
            with st.expander("추출된 텍스트 미리보기", expanded=False):
                st.text_area(
                    "추출 텍스트",
                    value=extracted_text[:5000] + ("..." if len(extracted_text) > 5000 else ""),
                    height=200,
                    disabled=True,
                )
        elif extracted_text.startswith("❌"):
            st.error(extracted_text)
else:
    st.info("📌 PDF 업로드를 사용하려면 `pip install pymupdf` 후 앱을 재시작하세요.")

st.markdown("---")

# 텍스트 입력 (PDF가 없을 때 또는 추가 질문)
default_prompt = "이 논문의 핵심 기여점, 방법론, 한계점을 요약해주세요."
user_question = st.text_input(
    "분석 질문 (선택 사항)",
    value=default_prompt,
    placeholder="예: 이 논문의 핵심 기여점과 한계점을 분석해주세요.",
)
user_text = st.text_area(
    "추가 텍스트 (PDF 없이 직접 입력할 때 사용)",
    height=150,
    placeholder="PDF 없이 텍스트만 분석할 경우 여기에 붙여넣으세요.",
)

# 실제 분석 대상: PDF 추출 텍스트 우선, 없으면 직접 입력 텍스트
if extracted_text and not extracted_text.startswith("❌"):
    content_to_analyze = extracted_text
elif user_text.strip():
    content_to_analyze = user_text.strip()
else:
    content_to_analyze = ""

# 분석에 사용할 최종 입력 (내용 + 질문)
if content_to_analyze:
    user_input = f"""[분석 요청]
{user_question}

[논문/텍스트 내용]
{content_to_analyze}
"""
else:
    user_input = user_question if user_question.strip() else ""

# 분석 시작 버튼
analyze_button = st.button("🚀 분석 시작", type="primary")


# =============================================================================
# 분석 실행 및 결과 표시
# =============================================================================
if analyze_button:
    if not user_input.strip():
        st.warning("⚠️ PDF를 업로드하거나, 텍스트/질문을 입력해주세요.")
        st.stop()

    if not available_ais:
        st.error("❌ 최소 1개 이상의 API 키를 입력해주세요.")
        st.stop()

    ai_list = list(available_ais.keys())

    # -------------------------------------------------------------------------
    # 일반 모드: 개별 답변 → 종합
    # -------------------------------------------------------------------------
    if not is_deep_mode:
        st.markdown("### 📋 1단계: 각 AI의 초기 분석")
        responses = {}
        with st.spinner("각 AI가 논문을 분석하고 있습니다..."):
            for ai_id, api_key in available_ais.items():
                prompt = f"""다음 논문 관련 내용을 분석해주세요. 연구자 관점에서 핵심을 짚어주세요.

---
{user_input}
---
"""
                try:
                    responses[ai_id] = CALL_FUNCTIONS[ai_id](api_key, prompt)
                except Exception as e:
                    responses[ai_id] = f"❌ 오류 발생: {str(e)}"

        cols = st.columns(min(len(responses), 3))
        for idx, (ai_id, resp) in enumerate(responses.items()):
            with cols[idx % len(cols)]:
                with st.expander(f"**{AI_CONFIG[ai_id]['name']}** 답변", expanded=True):
                    st.markdown(resp or "*답변 없음*")

        valid_responses = {
            k: v for k, v in responses.items()
            if v and "❌ 오류 발생" not in v
        }

    # -------------------------------------------------------------------------
    # 심층 토론 모드: A 답변 → B 검토 → A 수정 → 종합
    # -------------------------------------------------------------------------
    else:
        st.markdown("### 📋 심층 토론 모드: 상호 비판 (Cross-Review)")
        if len(ai_list) < 2:
            st.warning("⚠️ 심층 토론 모드에는 최소 2개 이상의 AI가 필요합니다. API 키를 더 추가하세요.")
            st.stop()

        # Round 1: 각 AI 초기 답변
        st.markdown("#### 1단계: 각 AI의 초기 답변")
        initial_responses = {}
        with st.spinner("각 AI가 초기 답변을 작성하고 있습니다..."):
            for ai_id, api_key in available_ais.items():
                prompt = f"""다음 논문 관련 내용을 분석해주세요. 연구자 관점에서 핵심을 짚어주세요.

---
{user_input}
---
"""
                try:
                    initial_responses[ai_id] = CALL_FUNCTIONS[ai_id](api_key, prompt)
                except Exception as e:
                    initial_responses[ai_id] = f"❌ 오류 발생: {str(e)}"

        for ai_id, resp in initial_responses.items():
            with st.expander(f"**{AI_CONFIG[ai_id]['name']}** 초기 답변", expanded=False):
                st.markdown(resp or "*답변 없음*")

        valid_initial = {
            k: v for k, v in initial_responses.items()
            if v and "❌ 오류 발생" not in v
        }
        if len(valid_initial) < 2:
            st.warning("유효한 답변이 2개 미만입니다. 심층 토론을 진행할 수 없습니다.")
            valid_responses = valid_initial
        else:
            # Round 2: B가 A의 답변 검토 (라운드 로빈)
            st.markdown("#### 2단계: 상호 검토 (논리적 오류·빠진 데이터 지적)")
            reviews = {}
            reviewer_ids = list(valid_initial.keys())
            for i, author_id in enumerate(reviewer_ids):
                reviewer_id = reviewer_ids[(i + 1) % len(reviewer_ids)]
                if author_id == reviewer_id:
                    continue
                author_resp = valid_initial[author_id]
                api_key = api_keys[reviewer_id]
                review_prompt = f"""다음은 다른 AI의 논문 분석 답변입니다.
당신의 역할: **비평가**. 이 답변에서 논리적 오류, 빠진 데이터, 부족한 근거, 또는 개선이 필요한 부분을 구체적으로 지적해주세요.

**검토 대상 답변 (작성: {AI_CONFIG[author_id]['name']}):**
---
{author_resp}
---
**지적 사항 (bullet point로 구체적으로):**
"""
                try:
                    review = CALL_FUNCTIONS[reviewer_id](api_key, review_prompt)
                    reviews[author_id] = (reviewer_id, review)
                except Exception as e:
                    reviews[author_id] = (reviewer_id, f"❌ 검토 오류: {str(e)}")

            for author_id, (reviewer_id, review_text) in reviews.items():
                with st.expander(
                    f"**{AI_CONFIG[reviewer_id]['name']}** → **{AI_CONFIG[author_id]['name']}** 검토",
                    expanded=False,
                ):
                    st.markdown(review_text or "*검토 없음*")

            # Round 3: A가 B의 지적을 반영하여 수정
            st.markdown("#### 3단계: 지적 반영 후 수정안")
            revised_responses = {}
            with st.spinner("각 AI가 검토 사항을 반영하여 수정안을 작성하고 있습니다..."):
                for author_id in valid_initial:
                    if author_id not in reviews:
                        revised_responses[author_id] = valid_initial[author_id]
                        continue
                    reviewer_id, review_text = reviews[author_id]
                    if "❌" in review_text:
                        revised_responses[author_id] = valid_initial[author_id]
                        continue
                    api_key = api_keys[author_id]
                    revise_prompt = f"""당신의 초기 답변에 대한 검토자가 지적한 내용이 있습니다.
이 지적을 **수용하여** 수정된 최종 답변을 작성해주세요. 지적이 타당하지 않다고 판단되면 그 이유를 briefly 설명하고 유지해도 됩니다.

**당신의 초기 답변:**
---
{valid_initial[author_id]}
---

**검토자 ({AI_CONFIG[reviewer_id]['name']})의 지적:**
---
{review_text}
---

**수정된 최종 답변:**
"""
                    try:
                        revised = CALL_FUNCTIONS[author_id](api_key, revise_prompt)
                        revised_responses[author_id] = revised
                    except Exception as e:
                        revised_responses[author_id] = valid_initial[author_id]

            for ai_id, resp in revised_responses.items():
                with st.expander(f"**{AI_CONFIG[ai_id]['name']}** 수정안", expanded=True):
                    st.markdown(resp or "*답변 없음*")

            valid_responses = {
                k: v for k, v in revised_responses.items()
                if v and "❌" not in v
            }

    st.markdown("---")

    # -------------------------------------------------------------------------
    # 최종 Consensus Report
    # -------------------------------------------------------------------------
    if len(valid_responses) < 1:
        st.warning("API 호출에 오류가 있어 Consensus Report를 생성할 수 없습니다.")
        st.stop()

    st.markdown("### 📊 Consensus Report (최종 종합)")

    response_texts = "\n\n".join(
        [
            f"**【{AI_CONFIG[ai_id]['name']}】의 답변:**\n{resp}"
            for ai_id, resp in valid_responses.items()
        ]
    )

    consensus_prompt = f"""다음은 동일한 논문/질문에 대한 여러 AI의 분석 결과입니다.
공통점과 차이점을 정리하고, 연구자에게 가장 유용한 최종 권장 분석을 작성해주세요. 한국어로 답변해주세요.

**원본 입력:**
{user_input}

---
**각 AI의 분석:**
{response_texts}
---

다음 형식으로 Consensus Report를 작성해주세요:

## 공통점
- 여러 AI가 일치하는 내용을 bullet point로 나열

## 차이점
- AI별로 관점이나 강조점이 다른 부분을 bullet point로 나열

## 최종 권장 분석
- 논문 연구나 후속 연구에 활용하기에 가장 적합한 종합적인 분석 및 권장 사항을 제시
"""

    synthesizer_id = list(valid_responses.keys())[0]
    synthesizer_key = api_keys[synthesizer_id]

    with st.spinner(f"{AI_CONFIG[synthesizer_id]['name']}가 최종 종합을 작성하고 있습니다..."):
        try:
            consensus = CALL_FUNCTIONS[synthesizer_id](synthesizer_key, consensus_prompt)
            st.markdown(consensus)
        except Exception as e:
            st.error(f"Consensus Report 생성 중 오류: {str(e)}")
