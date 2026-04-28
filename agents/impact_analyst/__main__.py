"""CLI runner for the Impact Analyst agent.

Usage examples
--------------
# Analyse a specific PR
python -m agents.impact_analyst "Analyse PR #42 in lokeshsharma99/GDS-Demo-App"

# Analyse by Issue number
python -m agents.impact_analyst "What tests are missing or obsolete for Issue #15?"

# General regression suite health check
python -m agents.impact_analyst "Review recent PRs and identify test suite gaps"
"""

from agents.impact_analyst import impact_analyst

impact_analyst.cli()
