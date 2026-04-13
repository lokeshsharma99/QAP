"""
Triage UI Endpoints
===================

API endpoints for the Triage UI to view failures, healing status, and statistics.
"""

import logging
from typing import Optional

from fastapi import HTTPException

logger = logging.getLogger(__name__)


# In-memory storage for demo purposes (would use database in production)
triage_failures = []
healing_history = []


def get_failures(limit: int = 50, offset: int = 0) -> list:
    """Get list of recent failures with RCA status."""
    return triage_failures[offset:offset + limit]


def get_failure(failure_id: str) -> Optional[dict]:
    """Get detailed RCA for a specific failure."""
    for failure in triage_failures:
        if failure.get("id") == failure_id:
            return failure
    return None


def get_healings(limit: int = 50, offset: int = 0) -> list:
    """Get list of healing history."""
    return healing_history[offset:offset + limit]


def get_stats() -> dict:
    """Get triage statistics (heal rate, common failures)."""
    total_failures = len(triage_failures)
    healed_failures = len([f for f in triage_failures if f.get("healed", False)])
    
    # Calculate heal rate
    heal_rate = (healed_failures / total_failures * 100) if total_failures > 0 else 0
    
    # Count failure types
    failure_types = {}
    for failure in triage_failures:
        ftype = failure.get("failure_type", "UNKNOWN")
        failure_types[ftype] = failure_types.get(ftype, 0) + 1
    
    return {
        "total_failures": total_failures,
        "healed_failures": healed_failures,
        "heal_rate": round(heal_rate, 2),
        "failure_types": failure_types,
    }


def trigger_healing(failure_id: str) -> dict:
    """Trigger healing for a specific failure."""
    failure = get_failure(failure_id)
    if not failure:
        raise HTTPException(status_code=404, detail="Failure not found")
    
    if not failure.get("is_healable", False):
        raise HTTPException(status_code=400, detail="Failure is not healable")
    
    # In a full implementation, this would:
    # 1. Trigger Triage-Heal workflow
    # 2. Track healing progress
    # 3. Update failure status
    
    return {
        "status": "initiated",
        "message": f"Healing initiated for failure {failure_id}",
        "failure_id": failure_id,
    }
