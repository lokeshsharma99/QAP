"""
Engineer Agent Reliability Evaluation
=====================================

Tests the Engineer agent's reliability in:
- Writing files to disk using FileTools
- Validating files were created
- Running linting verification
- Respecting file system restrictions
"""

import os
import sys
from pathlib import Path
from typing import Optional

# Add project root to sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agno.agent import Agent
from agno.eval.reliability import ReliabilityEval, ReliabilityResult
from agno.run.agent import RunOutput
from agno.tools.coding import CodingTools
from agno.tools.file import FileTools

from app.settings import MODEL
from agents.engineer.agent import engineer


def test_file_writing_reliability() -> Optional[ReliabilityResult]:
    """Test that the Engineer agent writes files to disk reliably."""
    try:
        response: RunOutput = engineer.run(
            "Create a simple Page Object for a login page with username and password fields in automation/pages/"
        )
        if response is None:
            print("ERROR: Agent run returned None")
            return None
        evaluation = ReliabilityEval(
            name="File Writing Reliability",
            agent_response=response,
            expected_tool_calls=["write_file"],
        )
        result = evaluation.run(print_results=True)
        return result
    except Exception as e:
        print(f"ERROR: {e}")
        return None


def test_linting_reliability() -> Optional[ReliabilityResult]:
    """Test that the Engineer agent runs linting after code generation."""
    try:
        response: RunOutput = engineer.run(
            "Generate a TypeScript file in automation/pages/ and run linting on it"
        )
        if response is None:
            print("ERROR: Agent run returned None")
            return None
        evaluation = ReliabilityEval(
            name="Linting Reliability",
            agent_response=response,
            expected_tool_calls=["run_linting"],
        )
        result = evaluation.run(print_results=True)
        return result
    except Exception as e:
        print(f"ERROR: {e}")
        return None


def test_file_validation_reliability() -> Optional[ReliabilityResult]:
    """Test that the Engineer agent validates files were created."""
    try:
        response: RunOutput = engineer.run(
            "Create a TypeScript file and validate it was created"
        )
        if response is None:
            print("ERROR: Agent run returned None")
            return None
        evaluation = ReliabilityEval(
            name="File Validation Reliability",
            agent_response=response,
            expected_tool_calls=["validate_files_created"],
        )
        result = evaluation.run(print_results=True)
        return result
    except Exception as e:
        print(f"ERROR: {e}")
        return None


if __name__ == "__main__":
    print("=" * 60)
    print("Engineer Agent Reliability Evaluation")
    print("=" * 60)
    
    print("\n1. Testing File Writing Reliability...")
    file_writing_result = test_file_writing_reliability()
    
    print("\n2. Testing Linting Reliability...")
    linting_result = test_linting_reliability()
    
    print("\n3. Testing File Validation Reliability...")
    validation_result = test_file_validation_reliability()
    
    print("\n" + "=" * 60)
    print("Evaluation Summary")
    print("=" * 60)
    print(f"File Writing: {file_writing_result.status if file_writing_result else 'Failed'}")
    print(f"Linting: {linting_result.status if linting_result else 'Failed'}")
    print(f"File Validation: {validation_result.status if validation_result else 'Failed'}")
