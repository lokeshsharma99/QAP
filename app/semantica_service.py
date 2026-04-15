"""
Semantica Service Layer
========================

Service layer for Semantica integration with Quality Autopilot.
Provides decision tracking, temporal intelligence, provenance tracking,
and context graph services with feature flag support.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from app.semantica_config import SemanticaContext


# ---------------------------------------------------------------------------
# Decision Tracking Service
# ---------------------------------------------------------------------------
class DecisionTrackingService:
    """Service for tracking agent decisions with causal chains."""

    @staticmethod
    def record_decision(
        category: str,
        scenario: str,
        reasoning: str,
        outcome: str,
        confidence: float,
        agent_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Record a decision with full reasoning context.

        Args:
            category: Decision category (e.g., "root_cause", "healing", "quality_gate")
            scenario: Context description for the decision
            reasoning: Explanation of why the decision was made
            outcome: The decision result
            confidence: Confidence score (0.0 to 1.0)
            agent_id: ID of the agent making the decision
            metadata: Additional metadata about the decision

        Returns:
            Decision ID if successful, None if Semantica is disabled or fails
        """
        if not SemanticaContext.is_decision_tracking_enabled():
            return None

        context_graph = SemanticaContext.get_context_graph()
        if context_graph is None:
            return None

        try:
            decision_id = context_graph.record_decision(
                category=category,
                scenario=scenario,
                reasoning=reasoning,
                outcome=outcome,
                confidence=confidence,
                **(metadata or {}),
            )
            return decision_id
        except Exception:
            # Gracefully handle errors - don't break agent execution
            return None

    @staticmethod
    def add_causal_relationship(
        from_decision_id: str,
        to_decision_id: str,
        relationship_type: str,
        agent_id: str,
    ) -> bool:
        """Link two decisions with a causal relationship.

        Args:
            from_decision_id: Source decision ID
            to_decision_id: Target decision ID
            relationship_type: Type of causal link (e.g., "enables", "causes", "precedes")
            agent_id: ID of the agent creating the relationship

        Returns:
            True if successful, False otherwise
        """
        if not SemanticaContext.is_decision_tracking_enabled():
            return False

        context_graph = SemanticaContext.get_context_graph()
        if context_graph is None:
            return False

        try:
            context_graph.add_causal_relationship(
                from_decision_id,
                to_decision_id,
                relationship_type=relationship_type,
            )
            return True
        except Exception:
            return False

    @staticmethod
    def trace_decision_chain(decision_id: str) -> Optional[List[Dict[str, Any]]]:
        """Trace the causal chain of a decision.

        Args:
            decision_id: Decision ID to trace

        Returns:
            List of decisions in the causal chain, or None if Semantica is disabled
        """
        if not SemanticaContext.is_decision_tracking_enabled():
            return None

        context_graph = SemanticaContext.get_context_graph()
        if context_graph is None:
            return None

        try:
            chain = context_graph.trace_decision_chain(decision_id)
            return chain
        except Exception:
            return None

    @staticmethod
    def find_similar_decisions(
        query: str,
        max_results: int = 5,
        agent_id: Optional[str] = None,
    ) -> Optional[List[Dict[str, Any]]]:
        """Find similar decisions using hybrid search.

        Args:
            query: Search query for similar decisions
            max_results: Maximum number of results to return
            agent_id: Optional agent ID to filter by

        Returns:
            List of similar decisions, or None if Semantica is disabled
        """
        if not SemanticaContext.is_decision_tracking_enabled():
            return None

        context_graph = SemanticaContext.get_context_graph()
        if context_graph is None:
            return None

        try:
            similar = context_graph.find_similar_decisions(query, max_results=max_results)
            return similar
        except Exception:
            return None

    @staticmethod
    def analyze_decision_impact(decision_id: str) -> Optional[Dict[str, Any]]:
        """Analyze the downstream impact of a decision.

        Args:
            decision_id: Decision ID to analyze

        Returns:
            Impact analysis results, or None if Semantica is disabled
        """
        if not SemanticaContext.is_decision_tracking_enabled():
            return None

        context_graph = SemanticaContext.get_context_graph()
        if context_graph is None:
            return None

        try:
            impact = context_graph.analyze_decision_impact(decision_id)
            return impact
        except Exception:
            return None

    @staticmethod
    def check_decision_rules(
        decision_data: Dict[str, Any],
        agent_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Check if a decision complies with business rules.

        Args:
            decision_data: Decision data to validate
            agent_id: ID of the agent making the decision

        Returns:
            Compliance check results, or None if Semantica is disabled
        """
        if not SemanticaContext.is_decision_tracking_enabled():
            return None

        context_graph = SemanticaContext.get_context_graph()
        if context_graph is None:
            return None

        try:
            compliance = context_graph.check_decision_rules(decision_data)
            return compliance
        except Exception:
            return None


# ---------------------------------------------------------------------------
# Temporal Service
# ---------------------------------------------------------------------------
class TemporalService:
    """Service for temporal intelligence and point-in-time queries."""

    @staticmethod
    def state_at(at_time: datetime) -> Optional[Any]:
        """Get the graph state at a specific point in time.

        Args:
            at_time: Timestamp to reconstruct the graph state

        Returns:
            Graph snapshot at the specified time, or None if Semantica is disabled
        """
        if not SemanticaContext.is_temporal_enabled():
            return None

        context_graph = SemanticaContext.get_context_graph()
        if context_graph is None:
            return None

        try:
            snapshot = context_graph.state_at(at_time)
            return snapshot
        except Exception:
            return None

    @staticmethod
    def rewrite_temporal_query(query: str) -> Optional[Dict[str, Any]]:
        """Parse temporal intent from natural language (zero LLM calls).

        Args:
            query: Natural language query with temporal expressions

        Returns:
            Parsed temporal intent with rewritten query, or None if Semantica is disabled
        """
        if not SemanticaContext.is_temporal_enabled():
            return None

        try:
            from semantica.kg import TemporalQueryRewriter

            rewriter = TemporalQueryRewriter()
            result = rewriter.rewrite(query)
            return {
                "temporal_intent": result.temporal_intent,
                "at_time": result.at_time,
                "rewritten_query": result.rewritten_query,
            }
        except Exception:
            return None

    @staticmethod
    def normalize_date_expression(expression: str) -> Optional[tuple]:
        """Normalize date expressions to UTC (zero LLM calls).

        Args:
            expression: Date expression (e.g., "Q1 2024", "effective from 2023-09-01")

        Returns:
            Tuple of (start_date, end_date) in UTC, or None if Semantica is disabled
        """
        if not SemanticaContext.is_temporal_enabled():
            return None

        try:
            from semantica.kg import TemporalNormalizer

            normalizer = TemporalNormalizer()
            start, end = normalizer.normalize(expression)
            return (start, end)
        except Exception:
            return None


# ---------------------------------------------------------------------------
# Provenance Service
# ---------------------------------------------------------------------------
class ProvenanceService:
    """Service for W3C PROV-O compliant provenance tracking."""

    @staticmethod
    def track_entity(
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
        if not SemanticaContext.is_provenance_enabled():
            return False

        try:
            from semantica.provenance import ProvenanceTracker

            ProvenanceTracker.track_entity(
                entity_id=entity_id,
                source=source,
                metadata=metadata or {},
            )
            return True
        except Exception:
            return False

    @staticmethod
    def track_algorithm(
        algorithm_name: str,
        input_data: Any,
        output_data: Any,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Track the computation lineage of an algorithm.

        Args:
            algorithm_name: Name of the algorithm
            input_data: Input data to the algorithm
            output_data: Output data from the algorithm
            metadata: Additional metadata

        Returns:
            True if successful, False otherwise
        """
        if not SemanticaContext.is_provenance_enabled():
            return False

        try:
            from semantica.provenance import AlgorithmTrackerWithProvenance

            tracker = AlgorithmTrackerWithProvenance()
            tracker.track(
                algorithm_name=algorithm_name,
                input_data=input_data,
                output_data=output_data,
                metadata=metadata or {},
            )
            return True
        except Exception:
            return False

    @staticmethod
    def get_lineage(entity_id: str) -> Optional[Dict[str, Any]]:
        """Get the lineage trace for an entity.

        Args:
            entity_id: ID of the entity

        Returns:
            Lineage information, or None if Semantica is disabled
        """
        if not SemanticaContext.is_provenance_enabled():
            return None

        try:
            from semantica.provenance import ProvenanceTracker

            lineage = ProvenanceTracker.get_lineage(entity_id)
            return lineage
        except Exception:
            return None


# ---------------------------------------------------------------------------
# Context Graph Service
# ---------------------------------------------------------------------------
class ContextGraphService:
    """Service for context graph queries and analysis."""

    @staticmethod
    def query_graph(
        query: str,
        agent_id: Optional[str] = None,
    ) -> Optional[List[Dict[str, Any]]]:
        """Query the context graph.

        Args:
            query: Graph query (natural language or structured)
            agent_id: Optional agent ID for context

        Returns:
            Query results, or None if Semantica is disabled
        """
        context_graph = SemanticaContext.get_context_graph()
        if context_graph is None:
            return None

        try:
            results = context_graph.query(query)
            return results
        except Exception:
            return None

    @staticmethod
    def analyze_decision_influence(decision_id: str) -> Optional[Dict[str, Any]]:
        """Analyze the influence of a decision on other decisions.

        Args:
            decision_id: Decision ID to analyze

        Returns:
            Influence analysis results, or None if Semantica is disabled
        """
        if not SemanticaContext.is_decision_tracking_enabled():
            return None

        context_graph = SemanticaContext.get_context_graph()
        if context_graph is None:
            return None

        try:
            influence = context_graph.analyze_decision_influence(decision_id)
            return influence
        except Exception:
            return None
