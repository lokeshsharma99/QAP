"""
Technical Tester Agent
=======================

Uses Playwright Test Agents (planner, generator, healer) for rapid test generation
and exploratory testing, complementing the existing BDD+POM workflow.
"""

from agents.technical_tester.agent import technical_tester

__all__ = ["technical_tester"]
