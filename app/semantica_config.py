"""
Semantica Configuration
=======================

Configuration layer for Semantica integration with Quality Autopilot.
Manages ContextGraph instances and feature flags for Semantica activation.
"""

from os import getenv
from typing import Optional

# ---------------------------------------------------------------------------
# Feature Flags
# ---------------------------------------------------------------------------
SEMANTICA_ENABLED = getenv("SEMANTICA_ENABLED", "false").lower() in ["true", "1", "yes"]
SEMANTICA_GRAPH_BACKEND = getenv("SEMANTICA_GRAPH_BACKEND", "pgvector")

# Per-agent feature flags (all disabled by default for gradual rollout)
SEMANTICA_DETECTIVE_ENABLED = getenv("SEMANTICA_DETECTIVE_ENABLED", "false").lower() in ["true", "1", "yes"]
SEMANTICA_MEDIC_ENABLED = getenv("SEMANTICA_MEDIC_ENABLED", "false").lower() in ["true", "1", "yes"]
SEMANTICA_JUDGE_ENABLED = getenv("SEMANTICA_JUDGE_ENABLED", "false").lower() in ["true", "1", "yes"]
SEMANTICA_CI_LOG_ANALYZER_ENABLED = getenv("SEMANTICA_CI_LOG_ANALYZER_ENABLED", "false").lower() in ["true", "1", "yes"]

# Per-feature feature flags
SEMANTICA_TEMPORAL_ENABLED = getenv("SEMANTICA_TEMPORAL_ENABLED", "false").lower() in ["true", "1", "yes"]
SEMANTICA_PROVENANCE_ENABLED = getenv("SEMANTICA_PROVENANCE_ENABLED", "false").lower() in ["true", "1", "yes"]
SEMANTICA_DECISION_TRACKING_ENABLED = getenv("SEMANTICA_DECISION_TRACKING_ENABLED", "false").lower() in ["true", "1", "yes"]


# ---------------------------------------------------------------------------
# Semantica Context Manager
# ---------------------------------------------------------------------------
class SemanticaContext:
    """Manages Semantica ContextGraph instances and feature flag checks."""

    _context_graph: Optional["ContextGraph"] = None
    _initialized: bool = False

    @classmethod
    def is_enabled(cls) -> bool:
        """Check if Semantica is globally enabled."""
        return SEMANTICA_ENABLED

    @classmethod
    def is_agent_enabled(cls, agent_id: str) -> bool:
        """Check if Semantica is enabled for a specific agent."""
        if not cls.is_enabled():
            return False

        agent_flags = {
            "detective": SEMANTICA_DETECTIVE_ENABLED,
            "medic": SEMANTICA_MEDIC_ENABLED,
            "judge": SEMANTICA_JUDGE_ENABLED,
            "healing_judge": SEMANTICA_JUDGE_ENABLED,
            "ci_log_analyzer": SEMANTICA_CI_LOG_ANALYZER_ENABLED,
        }

        return agent_flags.get(agent_id, False)

    @classmethod
    def is_temporal_enabled(cls) -> bool:
        """Check if temporal intelligence features are enabled."""
        return cls.is_enabled() and SEMANTICA_TEMPORAL_ENABLED

    @classmethod
    def is_provenance_enabled(cls) -> bool:
        """Check if provenance tracking features are enabled."""
        return cls.is_enabled() and SEMANTICA_PROVENANCE_ENABLED

    @classmethod
    def is_decision_tracking_enabled(cls) -> bool:
        """Check if decision tracking features are enabled."""
        return cls.is_enabled() and SEMANTICA_DECISION_TRACKING_ENABLED

    @classmethod
    def get_context_graph(cls) -> Optional["ContextGraph"]:
        """Get or create the shared ContextGraph instance.

        Returns:
            ContextGraph instance if Semantica is enabled, None otherwise.
        """
        if not cls.is_enabled():
            return None

        if not cls._initialized:
            cls._initialize_context_graph()
            cls._initialized = True

        return cls._context_graph

    @classmethod
    def _initialize_context_graph(cls) -> None:
        """Initialize the ContextGraph with appropriate backend configuration.

        This is called lazily on first access to avoid unnecessary initialization
        when Semantica is disabled.
        """
        try:
            from semantica.context import ContextGraph

            # Initialize ContextGraph with advanced analytics for decision tracking
            cls._context_graph = ContextGraph(advanced_analytics=True)

        except ImportError:
            # Semantica not installed, gracefully disable
            cls._context_graph = None
            cls._initialized = False

    @classmethod
    def reset(cls) -> None:
        """Reset the Semantica context (useful for testing)."""
        cls._context_graph = None
        cls._initialized = False


# ---------------------------------------------------------------------------
# Convenience Functions
# ---------------------------------------------------------------------------
def is_semantica_enabled() -> bool:
    """Check if Semantica is globally enabled."""
    return SemanticaContext.is_enabled()


def is_agent_semantica_enabled(agent_id: str) -> bool:
    """Check if Semantica is enabled for a specific agent."""
    return SemanticaContext.is_agent_enabled(agent_id)
