from pydantic import BaseModel, field_validator
from typing import Literal, Optional

class BankingResponse(BaseModel):
    intent: Literal[
        "loan_eligibility", "interest_rate", "kyc_process",
        "account_info", "guardrail_triggered", "off_topic"
    ]
    chain_of_thought: str
    response: str
    guardrail: Optional[Literal["pii_detected", "off_topic", "prompt_injection"]] = None
    disclaimer: Optional[str] = None

    @field_validator("chain_of_thought")
    @classmethod
    def cot_must_have_reasoning(cls, v):
        if len(v.split()) < 5:
            raise ValueError("Chain-of-thought must be at least 5 words")
        return v