"""
Shared guardrail instances for all Quality Autopilot agents.

Centralises the injection/PII guardrail configuration so patterns can be
updated in one place and stay consistent across every agent.

References:
  https://docs.agno.com/guardrails/included/prompt-injection
  https://docs.agno.com/guardrails/included/pii
"""

import re

from agno.guardrails import PIIDetectionGuardrail, PromptInjectionGuardrail

# ---------------------------------------------------------------------------
# PromptInjectionGuardrail
# injection_patterns REPLACES the default list — include all defaults + extras.
# Ref: https://docs.agno.com/guardrails/included/prompt-injection
# ---------------------------------------------------------------------------
prompt_injection_guardrail = PromptInjectionGuardrail(
    injection_patterns=[
        # --- Agno defaults ---
        "ignore previous instructions",
        "ignore your instructions",
        "you are now a",
        "forget everything above",
        "forget everything",
        "developer mode",
        "override safety",
        "disregard guidelines",
        "system prompt",
        "jailbreak",
        "act as if",
        "pretend you are",
        "roleplay as",
        "simulate being",
        "bypass restrictions",
        "ignore safeguards",
        "admin override",
        "root access",
        # --- Harmful / fraudulent intent ---
        "scam",
        "expose pii",
        "expose personal",
        "phishing",
        "commit fraud",
        "credit card fraud",
        "steal credentials",
        "steal credit card",
        "generate credit card",
        "identity theft",
        "dox someone",
        "doxxing",
        "generate malware",
        "write malware",
        "create ransomware",
        "write ransomware",
        "hack into",
        "exploit vulnerability",
        "sql injection attack",
        "ddos attack",
    ]
)

# ---------------------------------------------------------------------------
# PIIDetectionGuardrail
# custom_patterns EXTENDS the defaults (SSN, Credit Card, Email, Phone).
# Ref: https://docs.agno.com/guardrails/included/pii
# ---------------------------------------------------------------------------
pii_detection_guardrail = PIIDetectionGuardrail(
    enable_ssn_check=True,
    enable_credit_card_check=True,
    enable_email_check=True,
    enable_phone_check=True,
    custom_patterns={
        # IBAN — e.g. GB29NWBK60161331926819
        "IBAN": re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{4,30}\b"),
        # Passport number — e.g. A12345678
        "Passport": re.compile(r"\b[A-Z]{1,2}\d{6,9}\b"),
        # NHS number (UK) — 3-3-4 digit format
        "NHS Number": re.compile(r"\b\d{3}[\s-]\d{3}[\s-]\d{4}\b"),
    },
)
