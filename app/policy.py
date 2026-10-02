import re

HUMAN_PATTERNS = [
    r"真人", r"人工", r"客服人员", r"manager", r"supervisor", r"human agent",
    r"投诉", r"complaint", r"报警", r"police", r"律师", r"legal", r"起诉",
]

SENSITIVE_PATTERNS = [
    r"退款", r"refund", r"chargeback", r"盗刷", r"fraud", r"密码", r"password",
    r"验证码", r"otp", r"信用卡", r"credit card", r"付款", r"payment",
]


def explicit_handoff_reason(message: str) -> str | None:
    lowered = message.lower()
    for pattern in HUMAN_PATTERNS:
        if re.search(pattern, lowered, re.I):
            return "customer_requested_or_high_risk_human_review"
    for pattern in SENSITIVE_PATTERNS:
        if re.search(pattern, lowered, re.I):
            return "sensitive_account_or_financial_request"
    return None
