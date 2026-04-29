"""
Shared guardrail instances for all Quality Autopilot agents.

Centralises the injection/PII guardrail configuration so patterns can be
updated in one place and stay consistent across every agent.
"""

from agno.guardrails import PIIDetectionGuardrail, PromptInjectionGuardrail

# ---------------------------------------------------------------------------
# Injection patterns: default Agno list + harmful-content keywords
# ---------------------------------------------------------------------------
_INJECTION_PATTERNS: list[str] = [
    # --- Default Agno patterns ---
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
    # --- Harmful / fraudulent intent keywords ---
    "scam",
    "expose pii",
    "phishing",
    "commit fraud",
    "steal credentials",
    "steal credit card",
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
    "ddos",
]

# ---------------------------------------------------------------------------
# Shared guardrail instances — import these in every agent
# ---------------------------------------------------------------------------
prompt_injection_guardrail = PromptInjectionGuardrail(injection_patterns=_INJECTION_PATTERNS)
pii_detection_guardrail = PIIDetectionGuardrail()
