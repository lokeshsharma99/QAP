"""
Contracts Package
=================

Pydantic models for agent hand-off protocols.
Every transition between agents uses a structured contract defined here.
"""

from contracts.judge_verdict import JudgeVerdict
from contracts.gherkin_spec import GherkinSpec
from contracts.requirement_context import RequirementContext
from contracts.site_manifesto import SiteManifesto

__all__ = [
    "RequirementContext",
    "GherkinSpec",
    "JudgeVerdict",
    "SiteManifesto",
]
