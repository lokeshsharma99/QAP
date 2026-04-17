"""
Semantica Context Module
=======================

Provides decision intelligence, context graphs, and provenance tracking
for Quality Autopilot agents using Semantica framework.
"""

import logging
from typing import Optional

# Optional Semantica import - allows API to start without it installed
try:
    from semantica.context import AgentContext, ContextGraph
    from semantica.vector_store import VectorStore
    from semantica.graph_store import GraphStore
    SEMANTICA_AVAILABLE = True
except ImportError:
    SEMANTICA_AVAILABLE = False
    AgentContext = None
    ContextGraph = None
    VectorStore = None
    GraphStore = None

from app.settings import agent_db

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Global Semantica Context Instances
# ---------------------------------------------------------------------------

_judge_context: Optional[AgentContext] = None
_detective_context: Optional[AgentContext] = None
_librarian_context: Optional[AgentContext] = None


# ---------------------------------------------------------------------------
# Context Initialization
# ---------------------------------------------------------------------------

def get_judge_context() -> Optional[AgentContext]:
    """
    Get or initialize the Judge agent's Semantica context.
    
    The Judge uses decision intelligence to:
    - Track approval/rejection decisions with causal chains
    - Search precedents for consistent decisions
    - Analyze decision impact before auto-approval
    - Maintain W3C PROV-O compliant audit trails
    
    Returns None if Semantica is not installed.
    """
    global _judge_context
    
    if not SEMANTICA_AVAILABLE:
        logger.warning("Semantica is not installed. Decision intelligence features will be disabled.")
        return None
    
    if _judge_context is None:
        try:
            # Initialize vector store with PgVector backend
            vector_store = VectorStore(
                backend="pgvector",
                dimension=384,  # text-embedding-3-small dimension
                connection_string=str(agent_db.engine.url)
            )
            
            # Initialize context graph for decision tracking
            knowledge_graph = ContextGraph(
                advanced_analytics=True,
                centrality_analysis=True,
                community_detection=True,
                node_embeddings=True
            )
            
            # Initialize AgentContext with decision intelligence
            _judge_context = AgentContext(
                vector_store=vector_store,
                knowledge_graph=knowledge_graph,
                decision_tracking=True,
                graph_expansion=True,
                advanced_analytics=True,
                kg_algorithms=True,
                vector_store_features=True
            )
            
            logger.info("Semantica Judge context initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Judge context: {e}")
            # Fallback to in-memory if PgVector fails
            vector_store = VectorStore(backend="inmemory", dimension=384)
            _judge_context = AgentContext(
                vector_store=vector_store,
                decision_tracking=True
            )
            logger.warning("Judge context initialized with in-memory fallback")
    
    return _judge_context


def get_detective_context() -> Optional[AgentContext]:
    """
    Get or initialize the Detective agent's Semantica context.
    
    The Detective uses reasoning engines to:
    - Derive root causes from observed symptoms via forward chaining
    - Find most likely explanations via abductive reasoning
    - Pattern match failure classifications via Rete networks
    - Analyze temporal patterns in failures
    
    Returns None if Semantica is not installed.
    """
    global _detective_context
    
    if not SEMANTICA_AVAILABLE:
        logger.warning("Semantica is not installed. Reasoning engine features will be disabled.")
        return None
    
    if _detective_context is None:
        try:
            vector_store = VectorStore(
                backend="pgvector",
                dimension=384,
                connection_string=str(agent_db.engine.url)
            )
            
            _detective_context = AgentContext(
                vector_store=vector_store,
                decision_tracking=True,
                graph_expansion=True,
                advanced_analytics=True
            )
            
            logger.info("Semantica Detective context initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Detective context: {e}")
            vector_store = VectorStore(backend="inmemory", dimension=384)
            _detective_context = AgentContext(
                vector_store=vector_store,
                decision_tracking=True
            )
            logger.warning("Detective context initialized with in-memory fallback")
    
    return _detective_context


def get_librarian_context() -> Optional[AgentContext]:
    """
    Get or initialize the Librarian agent's Semantica context.
    
    The Librarian uses conflict detection to:
    - Detect contradictions between Site Manifesto and codebase KB
    - Resolve duplicate entities with different names
    - Detect temporal conflicts (old vs new information)
    - Apply multi-source conflict resolution strategies
    
    Returns None if Semantica is not installed.
    """
    global _librarian_context
    
    if not SEMANTICA_AVAILABLE:
        logger.warning("Semantica is not installed. Conflict detection features will be disabled.")
        return None
    
    if _librarian_context is None:
        try:
            vector_store = VectorStore(
                backend="pgvector",
                dimension=384,
                connection_string=str(agent_db.engine.url)
            )
            
            knowledge_graph = ContextGraph(
                advanced_analytics=True,
                centrality_analysis=True
            )
            
            _librarian_context = AgentContext(
                vector_store=vector_store,
                knowledge_graph=knowledge_graph,
                decision_tracking=True,
                graph_expansion=True
            )
            
            logger.info("Semantica Librarian context initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Librarian context: {e}")
            vector_store = VectorStore(backend="inmemory", dimension=384)
            _librarian_context = AgentContext(
                vector_store=vector_store,
                decision_tracking=True
            )
            logger.warning("Librarian context initialized with in-memory fallback")
    
    return _librarian_context


def reset_contexts():
    """Reset all Semantica contexts (useful for testing)."""
    global _judge_context, _detective_context, _librarian_context
    _judge_context = None
    _detective_context = None
    _librarian_context = None
    logger.info("All Semantica contexts reset")
