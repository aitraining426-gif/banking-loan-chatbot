import os
from dotenv import load_dotenv

load_dotenv()   # ← this line loads your .env file

import streamlit as st
import anthropic
import json
import yaml
from schemas.response_schema import BankingResponse
from guardrails.filters import run_guardrails

# ── Load prompt library ──────────────────────────────────────────
with open("prompts/prompt_library.yaml") as f:
    prompts = yaml.safe_load(f)

# ── Build system prompt from YAML ────────────────────────────────
def build_system_prompt() -> str:
    sp = prompts["system_prompt"]
    few_shots = "\n\n".join([
        f"User: {ex['user']}\nReasoning: {ex['cot']}\nResponse: {ex['response']}"
        for ex in prompts["few_shot_examples"]
    ])
    return f"""
{sp['role']}
Expertise: {', '.join(sp['expertise'])}

GUARDRAILS:
{sp['guardrails']}

OUTPUT FORMAT:
{sp['output_format']}

FEW-SHOT EXAMPLES:
{few_shots}
"""

# ── Anthropic client ──────────────────────────────────────────────
client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env

def query_claude(messages: list) -> BankingResponse:
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",  # faster and cheaper for testing
        max_tokens=1024,
        system=build_system_prompt(),
        messages=messages
    )

    # Step 1: get raw text
    raw = response.content[0].text if response.content else ""
    print("DEBUG raw response:", repr(raw[:300]))  # shows in terminal

    # Step 2: strip markdown fences if present
    clean = raw.strip()
    if clean.startswith("```"):
        clean = clean.split("```")[1]         # remove opening fence
        if clean.startswith("json"):
            clean = clean[4:]                 # remove 'json' label
    clean = clean.strip().rstrip("```").strip()

    print("DEBUG clean JSON:", repr(clean[:300]))  # shows in terminal

    # Step 3: parse with fallback
    if not clean:
        return BankingResponse(
            intent="off_topic",
            chain_of_thought="Model returned an empty response.",
            response="I'm sorry, I didn't receive a valid response. Please try again.",
            guardrail=None,
            disclaimer=None
        )

    try:
        data = json.loads(clean)
        return BankingResponse(**data)
    except json.JSONDecodeError as e:
        print("DEBUG JSON parse error:", e)
        print("DEBUG problematic text:", repr(clean))
        return BankingResponse(
            intent="off_topic",
            chain_of_thought=f"JSON parse failed: {e}",
            response="I encountered a formatting error. Please rephrase your question and try again.",
            guardrail=None,
            disclaimer=None
        )
    except Exception as e:
        print("DEBUG Pydantic error:", e)
        return BankingResponse(
            intent="off_topic",
            chain_of_thought=f"Validation error: {e}",
            response="I had trouble structuring my response. Please try again.",
            guardrail=None,
            disclaimer=None
        )
# ── Streamlit UI ──────────────────────────────────────────────────
st.set_page_config(page_title="Loan Risk Assistant", page_icon="🏦", layout="centered")
st.title("🏦 Loan Underwriting & Credit Risk Assistant")

# Session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Preset questions
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("Home loan eligibility"):
        st.session_state.preset = "Am I eligible for a ₹10 lakh home loan with ₹60k salary?"
with col2:
    if st.button("Interest rates"):
        st.session_state.preset = "What are the current savings account interest rates?"
with col3:
    if st.button("KYC process"):
        st.session_state.preset = "What documents are needed for KYC verification?"

# Chat display
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "assistant" and "parsed" in msg:
            p = msg["parsed"]
            col_a, col_b = st.columns([3, 1])
            with col_a:
                if p.guardrail:
                    st.error(p.response)
                else:
                    st.markdown(p.response)
            with col_b:
                st.caption(f"Intent: `{p.intent}`")
                if p.intent == "loan_eligibility":
                    with st.expander("Chain of thought"):
                        st.caption(p.chain_of_thought)
                if p.disclaimer:
                    st.caption(f"*{p.disclaimer}*")
        else:
            st.markdown(msg["content"])

# Input
user_input = st.chat_input("Ask about loans, interest rates, KYC...")
if hasattr(st.session_state, "preset") and st.session_state.preset:
    user_input = st.session_state.preset
    st.session_state.preset = None

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Run guardrails FIRST (before API call)
    guard_result = run_guardrails(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Analyzing..."):
            if guard_result:
                parsed = BankingResponse(**guard_result)
            else:
                api_messages = [
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.messages
                ]
                parsed = query_claude(api_messages)

            if parsed.guardrail:
                st.error(parsed.response)
            else:
                st.markdown(parsed.response)

    st.session_state.messages.append({
        "role": "assistant",
        "content": parsed.response,
        "parsed": parsed
    })
    st.rerun()