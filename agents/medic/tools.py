"""
Medic Agent Tools
=================

Tools for performing surgical edits to fix broken locators.
"""

import difflib
from pathlib import Path

from agno.tools import tool


@tool(
    name="apply_surgical_edit",
    description="Apply a HealingPatch to fix a broken locator in automation code",
)
def apply_surgical_edit(
    file_path: str,
    old_locator: str,
    new_locator: str,
    justification: str,
) -> str:
    """Apply a surgical edit to fix a broken locator.

    Args:
        file_path: Path to the file to edit (relative to automation/ directory)
        old_locator: The old locator that is broken
        new_locator: The new locator to replace it with
        justification: Reason for the change (from RCAReport)

    Returns:
        JSON string with result (success, message, lines_changed)
    """
    import json
    from pathlib import Path
    
    full_path = Path("automation") / file_path
    
    if not full_path.exists():
        return json.dumps({
            "success": False,
            "message": f"File not found: {full_path}",
            "lines_changed": 0,
        })
    
    try:
        # Read the file
        content = full_path.read_text()
        lines = content.split('\n')
        
        # Find and replace the old locator
        lines_changed = 0
        new_lines = []
        for line in lines:
            if old_locator in line:
                new_line = line.replace(old_locator, new_locator)
                new_lines.append(new_line)
                lines_changed += 1
            else:
                new_lines.append(line)
        
        if lines_changed == 0:
            return json.dumps({
                "success": False,
                "message": f"Old locator not found in file: {old_locator}",
                "lines_changed": 0,
            })
        
        # Write the file back
        full_path.write_text('\n'.join(new_lines))
        
        return json.dumps({
            "success": True,
            "message": f"Successfully replaced {old_locator} with {new_locator}",
            "lines_changed": lines_changed,
        })
    except Exception as e:
        return json.dumps({
            "success": False,
            "message": f"Error applying edit: {str(e)}",
            "lines_changed": 0,
        })


@tool(
    name="verify_edit_safety",
    description="Verify that a surgical edit doesn't break the code structure",
)
def verify_edit_safety(
    file_path: str,
    old_locator: str,
    new_locator: str,
) -> str:
    """Verify that a surgical edit is safe and won't break code.

    Args:
        file_path: Path to the file to verify
        old_locator: The old locator being replaced
        new_locator: The new locator to apply

    Returns:
        JSON string with safety check results (is_safe, issues)
    """
    import json
    from pathlib import Path
    
    full_path = Path("automation") / file_path
    issues = []
    
    if not full_path.exists():
        issues.append(f"File not found: {full_path}")
        return json.dumps({
            "is_safe": False,
            "issues": issues,
        })
    
    try:
        content = full_path.read_text()
        
        # Check if old locator exists
        if old_locator not in content:
            issues.append(f"Old locator not found in file: {old_locator}")
        
        # Check if new locator is different
        if old_locator == new_locator:
            issues.append("New locator is identical to old locator - no change needed")
        
        # Check for syntax issues (basic check)
        if new_locator.count('(') != new_locator.count(')'):
            issues.append("New locator has unbalanced parentheses")
        
        # Check for quote balance
        if new_locator.count('"') % 2 != 0 or new_locator.count("'") % 2 != 0:
            issues.append("New locator has unbalanced quotes")
        
        return json.dumps({
            "is_safe": len(issues) == 0,
            "issues": issues,
        })
    except Exception as e:
        issues.append(f"Error verifying edit: {str(e)}")
        return json.dumps({
            "is_safe": False,
            "issues": issues,
        })


@tool(
    name="rollback_edit",
    description="Rollback a surgical edit if verification fails",
)
def rollback_edit(
    file_path: str,
    old_locator: str,
    new_locator: str,
) -> str:
    """Rollback a surgical edit by reverting the locator change.

    Args:
        file_path: Path to the file to rollback
        old_locator: The original locator (to restore)
        new_locator: The new locator (to revert)

    Returns:
        JSON string with rollback result (success, message)
    """
    import json
    from pathlib import Path
    
    full_path = Path("automation") / file_path
    
    if not full_path.exists():
        return json.dumps({
            "success": False,
            "message": f"File not found: {full_path}",
        })
    
    try:
        content = full_path.read_text()
        
        # Revert the change (replace new with old)
        if new_locator not in content:
            return json.dumps({
                "success": False,
                "message": f"New locator not found in file: {new_locator}",
            })
        
        new_content = content.replace(new_locator, old_locator)
        full_path.write_text(new_content)
        
        return json.dumps({
            "success": True,
            "message": f"Successfully rolled back: {new_locator} → {old_locator}",
        })
    except Exception as e:
        return json.dumps({
            "success": False,
            "message": f"Error rolling back: {str(e)}",
        })


@tool(
    name="generate_healing_patch",
    description="Generate a HealingPatch from an RCAReport",
)
def generate_healing_patch(
    rca_report: str,
) -> str:
    """Generate a HealingPatch from an RCAReport.

    Args:
        rca_report: JSON string of RCAReport

    Returns:
        JSON string of HealingPatch
    """
    import json
    from datetime import datetime
    
    try:
        rca = json.loads(rca_report)
        
        # Only generate patch if failure is healable and is LOCATOR_STALE
        if not rca.get("is_healable", False):
            return json.dumps({
                "error": "RCAReport indicates failure is not healable",
                "rca_report": rca,
            })
        
        if rca.get("failure_type") != "LOCATOR_STALE":
            return json.dumps({
                "error": "RCAReport failure type is not LOCATOR_STALE",
                "rca_report": rca,
            })
        
        # Extract locator info from RCA
        locator_info = rca.get("affected_locator")
        if not locator_info:
            return json.dumps({
                "error": "RCAReport does not contain affected_locator information",
                "rca_report": rca,
            })
        
        # Generate HealingPatch
        old_locator_str = locator_info.get("locator", "")
        new_locator_str = locator_info.get("suggested_locator", "")
        
        # Generate unified diff
        diff_lines = list(difflib.unified_diff(
            [old_locator_str],
            [new_locator_str],
            fromfile=locator_info.get("file_path", ""),
            tofile=locator_info.get("file_path", ""),
            lineterm='',
            n=0
        ))
        diff = '\n'.join(diff_lines) if diff_lines else ""
        
        healing_patch = {
            "file_path": locator_info.get("file_path", ""),
            "old_locator": old_locator_str,
            "new_locator": new_locator_str,
            "diff": diff,
            "justification": rca.get("root_cause", ""),
            "rca_report_id": rca.get("test_name", ""),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "agent_id": "medic",
            "logic_changed": False,
            "verification_passes": 0,
            "verification_results": [],
        }
        
        return json.dumps(healing_patch, indent=2)
    except Exception as e:
        return json.dumps({
            "error": f"Error generating healing patch: {str(e)}",
            "rca_report": rca_report,
        })


@tool(
    name="run_verification_3x",
    description="Run test verification 3 times after applying a healing patch",
)
def run_verification_3x(
    file_path: str,
    test_name: str,
) -> str:
    """Run test verification 3 times and collect results.

    Args:
        file_path: Path to the file with the patch applied
        test_name: Name of the test to run

    Returns:
        JSON string with verification results (verification_results, verification_passes)
    """
    import json
    import subprocess
    
    results = []
    
    # Run test 3 times
    for i in range(3):
        try:
            # Run Playwright test in qap-playwright container
            result = subprocess.run(
                ["docker", "compose", "run", "qap-playwright", "npx", "playwright", "test", test_name],
                cwd="c:\\Users\\Lokesh-PC\\Downloads\\Quality AutoPilot",
                capture_output=True,
                text=True,
                timeout=60
            )
            
            # Check if test passed (return code 0)
            passed = result.returncode == 0
            results.append(passed)
            
        except subprocess.TimeoutExpired:
            results.append(False)
        except Exception as e:
            results.append(False)
    
    verification_passes = sum(results)
    
    return json.dumps({
        "verification_results": results,
        "verification_passes": verification_passes,
        "success": verification_passes >= 3,
        "message": f"Verification passed {verification_passes}/3 times",
    })
