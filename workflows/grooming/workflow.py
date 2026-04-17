"""
Grooming Workflow
================

Workflow for 3 Amigos user story review from BA, SDET, and Dev perspectives.
"""

from agno.workflow import Workflow, Step

from agents.architect import architect
from agents.engineer import engineer
from agents.judge import judge

# ---------------------------------------------------------------------------
# Create Workflow
# ---------------------------------------------------------------------------
grooming = Workflow(
    id="grooming",
    name="3 Amigos Grooming",
    steps=[
        Step(
            name="BA Assessment",
            agent=architect,
            description="""As the Business Analyst perspective, evaluate the user story from the provided Jira ticket.

Input: A Jira ticket ID (e.g., GDS-5) provided in the workflow input.

Your task:
1. Use fetch_jira_ticket tool to get the ticket details
2. Evaluate testability of the requirements (High/Medium/Low)
3. Assess completeness and clarity of requirements (True/False)
4. Provide additional notes from BA perspective

Output: Provide a BAAssessment with:
- testability: "high", "medium", or "low"
- completeness: true or false
- notes: your additional observations

Focus on: Are the requirements clear? Can they be tested? Is there missing information?""",
        ),
        Step(
            name="SDET Assessment",
            agent=judge,
            description="""As the SDET perspective, evaluate automation feasibility and risk.

Input: The Jira ticket details and BA assessment from previous step.

Your task:
1. Evaluate automation feasibility (High/Medium/Low)
2. Identify edge cases that need testing
3. Assess risk level for automation (Low/Medium/High)
4. Provide additional notes from SDET perspective

Output: Provide an SDETAssessment with:
- automation_feasibility: "high", "medium", or "low"
- edge_cases: list of identified edge cases
- risk_assessment: "low", "medium", or "high"
- notes: your additional observations

Focus on: Can this be automated? What are the tricky cases? What could go wrong?""",
        ),
        Step(
            name="Dev Assessment",
            agent=engineer,
            description="""As the Developer perspective, evaluate implementation complexity.

Input: The Jira ticket details and previous assessments.

Your task:
1. Assess implementation complexity (Low/Medium/High)
2. Identify dependencies or prerequisites
3. Provide additional notes from Dev perspective

Output: Provide a DevAssessment with:
- implementation_complexity: "low", "medium", or "high"
- dependencies: list of dependencies
- notes: your additional observations

Focus on: How complex is this to implement? What dependencies exist? Any technical challenges?""",
        ),
        Step(
            name="Synthesize Assessment",
            agent=judge,
            description="""Synthesize all three perspectives into a GroomingAssessment.

Input: BA assessment, SDET assessment, and Dev assessment from previous steps.

Your task:
1. Review all three assessments
2. Determine overall recommendation (Approve/Refine/Reject)
3. Create a GroomingAssessment with all fields populated
4. Provide rationale for the recommendation

Output: A GroomingAssessment JSON with:
- ticket_id: the Jira ticket ID
- requirement_context_id: link to RequirementContext (or empty if not generated)
- ba_assessment: the BA assessment
- sdet_assessment: the SDET assessment
- dev_assessment: the Dev assessment
- overall_recommendation: "approve", "refine", or "reject"
- timestamp: current ISO 8601 timestamp
- assessors: ["architect", "judge", "engineer"]

Recommendation criteria:
- Approve: All perspectives agree the story is ready
- Refine: Story needs clarification or refinement
- Reject: Story has significant issues""",
        ),
        Step(
            name="Post to Jira",
            agent=architect,
            description="""Post the GroomingAssessment as a comment to the Jira ticket.

Input: The GroomingAssessment from the previous step.

Your task:
1. Format the assessment as readable free-form text
2. Use add_jira_comment tool to post to the ticket
3. Include all key information from the assessment

Output: Confirmation that the comment was posted successfully.

The comment should include:
- Overall recommendation
- Summary of each perspective's assessment
- Any key concerns or notes
- Link to RequirementContext if available""",
        ),
    ],
)
