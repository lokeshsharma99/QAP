"""CLI runner for the Pipeline Analyst agent.

Usage examples
--------------
# Analyse the latest failed pipeline run
python -m agents.pipeline_analyst "Analyse the latest failed GitHub Actions run for lokeshsharma99/GDS-Demo-App"

# Analyse a specific run by ID
python -m agents.pipeline_analyst "Analyse workflow run #15234567890"

# Investigate a failure triggered by a specific PR
python -m agents.pipeline_analyst "Why did the pipeline fail for PR #42?"

# Get recurring failure patterns
python -m agents.pipeline_analyst "Show me recurring test failures from the last 5 pipeline runs"
"""

from agents.pipeline_analyst import pipeline_analyst

pipeline_analyst.cli()
