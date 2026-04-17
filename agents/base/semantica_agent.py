"""
Semantica Agent Base Class
===========================

Base class extending agno.Agent with Semantica integration.
Provides automatic decision recording, context graph queries,
and provenance tracking with feature flag support.
"""

from typing import Any, Dict, Optional

from agno.agent import Agent

from app.semantica_config import is_agent_semantica_enabled
from app.semantica_service import DecisionTrackingService, ProvenanceService


class SemanticaAgent(Agent):
    """Base agent class with Semantica integration.

    Automatically records decisions, tracks provenance, and provides
    context graph queries when Semantica is enabled for the agent.
    """

    def __init__(self, *args, **kwargs):
        """Initialize SemanticaAgent with optional Semantica integration.

        All agno.Agent parameters are supported. Semantica features are
        automatically enabled/disabled based on feature flags.
        """
        super().__init__(*args, **kwargs)

        # Store agent ID for Semantica tracking
        self._agent_id = kwargs.get("id", "unknown")
        self._semantica_enabled = is_agent_semantica_enabled(self._agent_id)

    def record_decision(
        self,
        category: str,
        scenario: str,
        reasoning: str,
        outcome: str,
        confidence: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Record a decision with full reasoning context.

        Args:
            category: Decision category (e.g., "root_cause", "healing")
            scenario: Context description for the decision
            reasoning: Explanation of why the decision was made
            outcome: The decision result
            confidence: Confidence score (0.0 to 1.0)
            metadata: Additional metadata about the decision

        Returns:
            Decision ID if successful, None if Semantica is disabled
        """
        if not self._semantica_enabled:
            return None

        return DecisionTrackingService.record_decision(
            category=category,
            scenario=scenario,
            reasoning=reasoning,
            outcome=outcome,
            confidence=confidence,
            agent_id=self._agent_id,
            metadata=metadata,
        )

    def add_causal_relationship(
        self,
        from_decision_id: str,
        to_decision_id: str,
        relationship_type: str,
    ) -> bool:
        """Link two decisions with a causal relationship.

        Args:
            from_decision_id: Source decision ID
            to_decision_id: Target decision ID
            relationship_type: Type of causal link (e.g., "enables", "causes")

        Returns:
            True if successful, False otherwise
        """
        if not self._semantica_enabled:
            return False

        return DecisionTrackingService.add_causal_relationship(
            from_decision_id=from_decision_id,
            to_decision_id=to_decision_id,
            relationship_type=relationship_type,
            agent_id=self._agent_id,
        )

    def trace_decision_chain(self, decision_id: str) -> Optional[list]:
        """Trace the causal chain of a decision.

        Args:
            decision_id: Decision ID to trace

        Returns:
            List of decisions in the causal chain, or None if Semantica is disabled
        """
        if not self._semantica_enabled:
            return None

        return DecisionTrackingService.trace_decision_chain(decision_id)

    def find_similar_decisions(
        self,
        query: str,
        max_results: int = 5,
    ) -> Optional[list]:
        """Find similar decisions using hybrid search.

        Args:
            query: Search query for similar decisions
            max_results: Maximum number of results to return

        Returns:
            List of similar decisions, or None if Semantica is disabled
        """
        if not self._semantica_enabled:
            return None

        return DecisionTrackingService.find_similar_decisions(
            query=query,
            max_results=max_results,
            agent_id=self._agent_id,
        )

    def track_entity_provenance(
        self,
        entity_id: str,
        source: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Track the provenance of an entity.

        Args:
            entity_id: ID of the entity to track
            source: Source of the entity (URL, file, etc.)
            metadata: Additional metadata about the entity

        Returns:
            True if successful, False otherwise
        """
        if not self._semantica_enabled:
            return False

        return ProvenanceService.track_entity(
            entity_id=entity_id,
            source=source,
            metadata=metadata,
        )

    def get_entity_lineage(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Get the lineage trace for an entity.

        Args:
            entity_id: ID of the entity

        Returns:
            Lineage information, or None if Semantica is disabled
        """
        if not self._semantica_enabled:
            return None

        return ProvenanceService.get_lineage(entity_id)

    @property
    def semantica_enabled(self) -> bool:
        """Check if Semantica is enabled for this agent."""
        return self._semantica_enabled
