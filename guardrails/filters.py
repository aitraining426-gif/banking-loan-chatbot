import re

PII_PATTERNS = {
    "aadhaar": r"\b\d{4}\s?\d{4}\s?\d{4}\b",
    "pan": r"\b[A-Z]{5}[0-9]{4}[A-Z]\b",
    "account_number": r"\b\d{9,18}\b",
    "otp": r"\b(otp|one.time.password)\s*[:\-]?\s*\d{4,8}\b",
}

INJECTION_PHRASES = [
    "ignore previous instructions",
    "ignore all instructions",
    "act as",
    "pretend you are",
    "jailbreak",
    "you are now",
    "forget your instructions",
    "disregard",
]

OFF_TOPIC_KEYWORDS = [
    "cricket", "recipe", "movie", "weather", "stock market",
    "sports", "celebrity", "politics", "religion",
]

def detect_pii(text: str) -> str | None:
    for pii_type, pattern in PII_PATTERNS.items():
        if re.search(pattern, text, re.IGNORECASE):
            return pii_type
    return None

def detect_injection(text: str) -> bool:
    text_lower = text.lower()
    return any(phrase in text_lower for phrase in INJECTION_PHRASES)

def detect_off_topic(text: str) -> bool:
    text_lower = text.lower()
    return any(kw in text_lower for kw in OFF_TOPIC_KEYWORDS)

def run_guardrails(user_input: str) -> dict | None:
    pii = detect_pii(user_input)
    if pii:
        return {
            "intent": "guardrail_triggered",
            "chain_of_thought": f"Detected sensitive PII of type {pii} in the user message. Must not process or repeat this value.",
            "response": "⚠️ Please do NOT share sensitive personal information (Aadhaar, PAN, account numbers, OTP) in this chat. Visit your bank branch or use official channels for secure submission.",
            "guardrail": "pii_detected",
            "disclaimer": None
        }
    if detect_injection(user_input):
        return {
            "intent": "guardrail_triggered",
            "chain_of_thought": "A prompt injection attempt was detected in the user message. Staying in banking assistant role and refusing to comply.",
            "response": "I can only help with banking and loan-related questions. Please ask about loans, interest rates, KYC, or account types.",
            "guardrail": "prompt_injection",
            "disclaimer": None
        }
    if detect_off_topic(user_input):
        return {
            "intent": "off_topic",
            "chain_of_thought": "The user query is outside the banking and finance domain. Politely redirecting to relevant topics.",
            "response": "I'm specialized in banking and loan services. I can help with loan eligibility, interest rates, KYC processes, and account information.",
            "guardrail": "off_topic",
            "disclaimer": None
        }
    return None