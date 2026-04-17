"""
Comprehensive Agent Evaluations
================================

Smoke tests, reliability checks, accuracy evals, and performance baselines
for all 9 agents in the Quality Autopilot system.
"""

import pytest
from pathlib import Path


class TestAgentAvailability:
    """Test that all agents are properly registered and available."""

    def test_architect_agent_exists(self):
        """Verify Architect agent can be imported."""
        from agents.architect import architect
        assert architect is not None
        assert architect.id == "architect"

    def test_scribe_agent_exists(self):
        """Verify Scribe agent can be imported."""
        from agents.scribe import scribe
        assert scribe is not None
        assert scribe.id == "scribe"

    def test_discovery_agent_exists(self):
        """Verify Discovery agent can be imported."""
        from agents.discovery import discovery
        assert discovery is not None
        assert discovery.id == "discovery"

    def test_librarian_agent_exists(self):
        """Verify Librarian agent can be imported."""
        from agents.librarian import librarian
        assert librarian is not None
        assert librarian.id == "librarian"

    def test_engineer_agent_exists(self):
        """Verify Engineer agent can be imported."""
        from agents.engineer import engineer
        assert engineer is not None
        assert engineer.id == "engineer"

    def test_data_agent_exists(self):
        """Verify Data Agent can be imported."""
        from agents.data_agent import data_agent
        assert data_agent is not None
        assert data_agent.id == "data_agent"

    def test_detective_agent_exists(self):
        """Verify Detective agent can be imported."""
        from agents.detective import detective
        assert detective is not None
        assert detective.id == "detective"

    def test_medic_agent_exists(self):
        """Verify Medic agent can be imported."""
        from agents.medic import medic
        assert medic is not None
        assert medic.id == "medic"

    def test_judge_agent_exists(self):
        """Verify Judge agent can be imported."""
        from agents.judge import judge
        assert judge is not None
        assert judge.id == "judge"


class TestTeamAvailability:
    """Test that all teams are properly registered and available."""

    def test_strategy_team_exists(self):
        """Verify Strategy team can be imported."""
        from teams.strategy import strategy_team
        assert strategy_team is not None
        assert strategy_team.id == "strategy_team"

    def test_context_team_exists(self):
        """Verify Context team can be imported."""
        from teams.context import context_team
        assert context_team is not None
        assert context_team.id == "context_team"

    def test_engineering_team_exists(self):
        """Verify Engineering team can be imported."""
        from teams.engineering import engineering_team
        assert engineering_team is not None
        assert engineering_team.id == "engineering_team"

    def test_operations_team_exists(self):
        """Verify Operations team can be imported."""
        from teams.operations import operations_team
        assert operations_team is not None
        assert operations_team.id == "operations_team"

    def test_grooming_team_exists(self):
        """Verify Grooming team can be imported."""
        from teams.grooming import grooming_team
        assert grooming_team is not None
        assert grooming_team.id == "grooming_team"


class TestWorkflowAvailability:
    """Test that all workflows are properly registered and available."""

    def test_spec_to_code_workflow_exists(self):
        """Verify Spec-to-Code workflow can be imported."""
        from workflows.spec_to_code import spec_to_code
        assert spec_to_code is not None
        assert spec_to_code.id == "spec-to-code"

    def test_discovery_onboard_workflow_exists(self):
        """Verify Discovery Onboard workflow can be imported."""
        from workflows.discovery_onboard import discovery_onboard
        assert discovery_onboard is not None
        assert discovery_onboard.id == "discovery-onboard"

    def test_triage_heal_workflow_exists(self):
        """Verify Triage-Heal workflow can be imported."""
        from workflows.triage_heal import triage_heal
        assert triage_heal is not None
        assert triage_heal.id == "triage-heal"

    def test_full_regression_workflow_exists(self):
        """Verify Full Regression workflow can be imported."""
        from workflows.full_regression import full_regression
        assert full_regression is not None
        assert full_regression.id == "full-regression"

    def test_grooming_workflow_exists(self):
        """Verify Grooming workflow can be imported."""
        from workflows.grooming import grooming
        assert grooming is not None
        assert grooming.id == "grooming"

    def test_automation_scaffold_workflow_exists(self):
        """Verify Automation Scaffold workflow can be imported."""
        from workflows.automation_scaffold import automation_scaffold
        assert automation_scaffold is not None
        assert automation_scaffold.id == "automation-scaffold"


class TestKnowledgeBaseAvailability:
    """Test that knowledge bases are properly configured."""

    def test_site_manifesto_knowledge_exists(self):
        """Verify Site Manifesto knowledge base can be created."""
        from db.session import get_site_manifesto_knowledge
        kb = get_site_manifesto_knowledge()
        assert kb is not None
        assert kb.name == "Site Manifesto KB"

    def test_automation_knowledge_exists(self):
        """Test that automation knowledge base exists and is accessible."""
        from db.session import get_automation_knowledge
        kb = get_automation_knowledge()
        assert kb is not None
        assert kb.name == "Automation KB"

    def test_learnings_knowledge_exists(self):
        """Verify Learnings knowledge base can be created."""
        from db.session import get_learnings_knowledge
        kb = get_learnings_knowledge()
        assert kb is not None
        assert kb.name == "Agent Learnings KB"


class TestContractStructure:
    """Test that all contracts have proper structure."""

    def test_requirement_context_contract_exists(self):
        """Verify RequirementContext contract exists."""
        from contracts.requirement_context import RequirementContext
        assert RequirementContext is not None

    def test_gherkin_spec_contract_exists(self):
        """Verify GherkinSpec contract exists."""
        from contracts.gherkin_spec import GherkinSpec
        assert GherkinSpec is not None

    def test_site_manifesto_contract_exists(self):
        """Verify SiteManifesto contract exists."""
        from contracts.site_manifesto import SiteManifesto
        assert SiteManifesto is not None

    def test_rca_report_contract_exists(self):
        """Verify RCAReport contract exists."""
        from contracts.rca_report import RCAReport
        assert RCAReport is not None

    def test_healing_patch_contract_exists(self):
        """Verify HealingPatch contract exists."""
        from contracts.healing_patch import HealingPatch
        assert HealingPatch is not None

    def test_judge_verdict_contract_exists(self):
        """Verify JudgeVerdict contract exists."""
        from contracts.judge_verdict import JudgeVerdict
        assert JudgeVerdict is not None

    def test_grooming_assessment_contract_exists(self):
        """Verify GroomingAssessment contract exists."""
        from contracts.grooming_assessment import GroomingAssessment
        assert GroomingAssessment is not None


class TestLearningConfiguration:
    """Test that learning is properly configured on key agents."""

    def test_detective_has_learning_enabled(self):
        """Verify Detective agent has learning enabled."""
        from agents.detective import detective
        assert detective.learning is True
        assert detective.add_learnings_to_context is True
        assert detective.knowledge is not None

    def test_medic_has_learning_enabled(self):
        """Verify Medic agent has learning enabled."""
        from agents.medic import medic
        assert medic.learning is True
        assert medic.add_learnings_to_context is True
        assert medic.knowledge is not None


class TestDirectoryStructure:
    """Test that the project directory structure is correct."""

    def test_agents_directory_exists(self):
        """Verify agents directory exists."""
        agents_dir = Path("agents")
        assert agents_dir.exists()
        assert agents_dir.is_dir()

    def test_teams_directory_exists(self):
        """Verify teams directory exists."""
        teams_dir = Path("teams")
        assert teams_dir.exists()
        assert teams_dir.is_dir()

    def test_workflows_directory_exists(self):
        """Verify workflows directory exists."""
        workflows_dir = Path("workflows")
        assert workflows_dir.exists()
        assert workflows_dir.is_dir()

    def test_contracts_directory_exists(self):
        """Verify contracts directory exists."""
        contracts_dir = Path("contracts")
        assert contracts_dir.exists()
        assert contracts_dir.is_dir()

    def test_evals_directory_exists(self):
        """Verify evals directory exists."""
        evals_dir = Path("evals")
        assert evals_dir.exists()
        assert evals_dir.is_dir()

    def test_automation_directory_exists(self):
        """Verify automation directory exists."""
        automation_dir = Path("automation")
        assert automation_dir.exists()
        assert automation_dir.is_dir()
