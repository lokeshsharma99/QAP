"""
Data Agent Tools
================

Custom tools for the Data Agent.
"""

import json
import uuid
from datetime import datetime
from typing import Optional
from concurrent.futures import TimeoutError as FutureTimeoutError

from agno.tools import tool
from faker import Faker

# Initialize Faker with UK locale for realistic UK data
fake = Faker('en_GB')

# In-memory cache for low-latency data access
_data_cache = {}

# Field type configuration: which fields are text_input (dynamic) vs lookup_dropdown (static)
FIELD_TYPE_CONFIG = {
    'username': 'text_input',
    'email': 'text_input',
    'phone': 'text_input',
    'address': 'text_input',
    'password': 'text_input',
    'national_insurance_number': 'text_input',
    'postcode': 'lookup_dropdown',  # Usually from predefined list
    'date_of_birth': 'lookup_dropdown',  # Usually from predefined ranges
}

# Duplicate-prone fields that need UUID-based uniqueness
DUPLICATE_PRONE_FIELDS = ['username', 'email', 'phone']

# Maximum retry attempts for database conflicts
MAX_RETRY_ATTEMPTS = 3


@tool(
    name="generate_dynamic_test_user",
    description="Generate a dynamic test user with unique, realistic data using Faker. UUID only applied to duplicate-prone fields.",
)
def generate_dynamic_test_user(
    use_cache: bool = False,
    timeout_seconds: int = 30,
) -> str:
    """Generate a dynamic test user with unique, realistic data.

    Args:
        use_cache: Whether to use cached data (default: False for fresh generation)
        timeout_seconds: Maximum time to wait for generation (default: 30 seconds)

    Returns:
        JSON string with dynamic test user data including unique identifiers
    """
    # Generate base timestamp
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
    full_uuid = str(uuid.uuid4())
    short_uuid = full_uuid[:8]
    
    # Generate dynamic data using Faker
    first_name = fake.first_name()
    last_name = fake.last_name()
    
    # Generate username (duplicate-prone: use UUID)
    username = f"testuser_{timestamp}_{short_uuid}"
    
    # Generate email (duplicate-prone: use UUID)
    email = f"{first_name.lower()}.{last_name.lower()}.{timestamp}@example.com"
    
    # Generate phone (duplicate-prone: use UUID)
    phone = fake.phone_number()
    
    # Generate UK National Insurance Number (text_input: dynamic, not duplicate-prone)
    nin_prefix = fake.random_element(['AB', 'CD', 'EF', 'GH', 'IJ', 'KL', 'MN', 'OP', 'QR', 'ST'])
    nin_number = fake.numerify(text='## ## ##')
    nin_suffix = fake.random_element(['A', 'B', 'C', 'D'])
    national_insurance_number = f"{nin_prefix} {nin_number} {nin_suffix}"
    
    # Generate dynamic address (text_input: dynamic, not duplicate-prone)
    address_line1 = fake.street_address()
    city = fake.city()
    postcode = fake.postcode()
    full_address = f"{address_line1}, {city}, {postcode}"
    
    # Generate date of birth (lookup_dropdown: static range, not duplicate-prone)
    date_of_birth = fake.date_of_birth(minimum_age=18, maximum_age=70).strftime('%Y-%m-%d')
    
    # Generate dynamic password (text_input: dynamic, not duplicate-prone)
    password = fake.password(length=12, special_chars=True, digits=True, upper_case=True)
    
    test_user = {
        "username": username,
        "password": password,
        "email": email,
        "phone": phone,
        "national_insurance_number": national_insurance_number,
        "address": full_address,
        "postcode": postcode,
        "date_of_birth": date_of_birth,
        "first_name": first_name,
        "last_name": last_name,
        "pii_masked": True,
        "unique_id": full_uuid,
        "generated_at": timestamp,
        "custom_fields": {},
        "field_types": FIELD_TYPE_CONFIG,
    }
    
    # Cache if requested
    if use_cache:
        _data_cache[full_uuid] = test_user
    
    return json.dumps(test_user, indent=2)


@tool(
    name="get_test_data_on_demand",
    description="Get test data on-demand with low-latency in-memory caching. Returns cached data if available, otherwise generates fresh data.",
)
def get_test_data_on_demand(
    data_type: str = "user",
    cache_key: Optional[str] = None,
    timeout_seconds: int = 30,
) -> str:
    """Get test data on-demand with caching for low-latency access.

    Args:
        data_type: Type of data to generate (default: "user")
        cache_key: Optional cache key to retrieve specific cached data
        timeout_seconds: Maximum time to wait for generation (default: 30 seconds)

    Returns:
        JSON string with test data
    """
    # Check cache first for low latency
    if cache_key and cache_key in _data_cache:
        return json.dumps({
            "status": "cached",
            "data": _data_cache[cache_key],
            "latency_ms": "<1"
        }, indent=2)
    
    # Generate fresh data
    if data_type == "user":
        user_data = json.loads(generate_dynamic_test_user(use_cache=True, timeout_seconds=timeout_seconds))
        return json.dumps({
            "status": "generated",
            "data": user_data,
            "latency_ms": "<10"
        }, indent=2)
    
    return json.dumps({
        "status": "error",
        "message": f"Unknown data type: {data_type}"
    }, indent=2)


@tool(
    name="generate_run_context",
    description="Generate a RunContext with dynamic test data and configuration for Playwright tests",
)
def generate_run_context(
    feature_file: str = "",
    environment: str = "test",
    base_url: str = "http://localhost:3000",
    use_dynamic_data: bool = True,
    timeout_seconds: int = 30,
    max_retries: int = MAX_RETRY_ATTEMPTS,
) -> str:
    """Generate a RunContext with dynamic test data and configuration.

    Args:
        feature_file: Path to the .feature file for context
        environment: Target environment (test, staging, production)
        base_url: Base URL of the application under test
        use_dynamic_data: Whether to use dynamic Faker data (default: True)
        timeout_seconds: Maximum time to wait for generation (default: 30 seconds)
        max_retries: Maximum retry attempts for database conflicts (default: 3)

    Returns:
        str: RunContext configuration as a JSON string
    """
    retry_count = 0
    last_error = None
    
    while retry_count < max_retries:
        try:
            if use_dynamic_data:
                # Use dynamic data generation
                test_user_data = json.loads(generate_dynamic_test_user(timeout_seconds=timeout_seconds))
                username = test_user_data["username"]
                password = test_user_data["password"]
                email = test_user_data["email"]
                phone = test_user_data["phone"]
                national_insurance_number = test_user_data["national_insurance_number"]
                address = test_user_data["address"]
                postcode = test_user_data["postcode"]
                date_of_birth = test_user_data["date_of_birth"]
                unique_id = test_user_data["unique_id"]
                field_types = test_user_data.get("field_types", FIELD_TYPE_CONFIG)
            else:
                # Fallback to static generation (original behavior)
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                unique_id = str(uuid.uuid4())[:8]
                username = f"testuser_{timestamp}_{unique_id}"
                password = "TestPass123!"
                email = f"{username}@example.com"
                phone = "07700900000"
                national_insurance_number = "QQ123456C"
                address = "123 Test Street, Test City, TC1 1AA"
                postcode = "TC1 1AA"
                date_of_birth = "1990-01-01"
                field_types = FIELD_TYPE_CONFIG

            run_context = {
                "test_user": {
                    "username": username,
                    "password": password,
                    "email": email,
                    "phone": phone,
                    "national_insurance_number": national_insurance_number,
                    "address": address,
                    "postcode": postcode,
                    "date_of_birth": date_of_birth,
                    "pii_masked": True,
                    "unique_id": unique_id,
                    "custom_fields": {},
                    "field_types": field_types,
                },
                "db_seed_queries": [
                    f"INSERT INTO users (username, password, email, phone, nin, address, postcode, dob, unique_id, created_at) VALUES ('{username}', 'hashed_password', '{email}', '{phone}', '{national_insurance_number}', '{address}', '{postcode}', '{date_of_birth}', '{unique_id}', NOW());"
                ],
                "api_mocks": {
                    "/api/external-service": {
                        "status": 200,
                        "body": {"status": "success", "data": "mocked_response"},
                    }
                },
                "cleanup_queries": [
                    f"DELETE FROM users WHERE unique_id = '{unique_id}';"
                ],
                "environment": environment,
                "base_url": base_url,
                "browser_config": {
                    "viewport": "1280x720",
                    "device": "desktop",
                },
                "timeout_ms": 30000,
                "retry_on_failure": True,
                "max_retries": max_retries,
                "retry_attempt": retry_count,
            }

            return json.dumps(run_context, indent=2)
            
        except Exception as e:
            retry_count += 1
            last_error = str(e)
            if retry_count >= max_retries:
                # Return error after max retries
                return json.dumps({
                    "status": "error",
                    "message": f"Failed to generate run context after {max_retries} attempts",
                    "error": last_error,
                    "retry_count": retry_count
                }, indent=2)
            # Continue to next retry
    
    # Fallback return (should not reach here)
    return json.dumps({
        "status": "error",
        "message": "Failed to generate run context",
        "error": last_error
    }, indent=2)


@tool(
    name="clear_data_cache",
    description="Clear the in-memory data cache. Useful for cleanup or starting fresh.",
)
def clear_data_cache() -> str:
    """Clear the in-memory data cache.

    Returns:
        JSON string with cache clear status
    """
    cache_size = len(_data_cache)
    _data_cache.clear()

    return json.dumps({
        "status": "success",
        "message": f"Cleared {cache_size} items from data cache",
        "cache_size_after": len(_data_cache)
    }, indent=2)


# ---------------------------------------------------------------------------
# Journey-aware data provisioning
# ---------------------------------------------------------------------------

# Maps a journey step name to the fields it needs from the RunContext.
_JOURNEY_STEP_FIELDS: dict[str, list[str]] = {
    # Authentication
    "login":               ["email", "password"],
    "register":            ["username", "email", "password", "phone"],
    "logout":              [],

    # Profile / personal details
    "fill_profile":        ["first_name", "last_name", "email", "phone", "date_of_birth"],
    "personal_details":    ["first_name", "last_name", "national_insurance_number",
                           "date_of_birth", "address", "postcode"],
    "update_address":      ["address", "postcode"],
    "change_password":     ["password"],
    "change_email":        ["email"],

    # Forms
    "contact_form":        ["first_name", "last_name", "email", "phone"],
    "checkout":            ["first_name", "last_name", "email", "address", "postcode"],
    "payment":             ["first_name", "last_name"],

    # Generic fallback — all fields
    "default":             ["username", "email", "password", "phone", "first_name",
                           "last_name", "date_of_birth", "address", "postcode",
                           "national_insurance_number"],
}


@tool(
    name="generate_scenario_data",
    description=(
        "Generate complete, journey-aware test data for a multi-step user journey. "
        "Accepts a GherkinSpec or list of journey steps and returns a RunContext where "
        "every step has exactly the fields it needs — login gets email+password, "
        "personal details form gets NIN+DOB+address, etc. "
        "Also writes the RunContext to automation/data/<ticket_id>.json automatically."
    ),
)
def generate_scenario_data(
    ticket_id: str,
    journey_steps: list[str],
    environment: str = "test",
    base_url: str = "",
    extra_fields: Optional[dict] = None,
) -> str:
    """Provision all data needed for a full user journey.

    Call this instead of generate_run_context when you know the test scenario's
    step sequence (e.g. from a GherkinSpec or from RequirementContext.acceptance_criteria).

    Args:
        ticket_id: Jira/ADO ticket ID — also used as the output filename stem.
        journey_steps: List of step names from the scenario, e.g.
                       ["login", "personal_details", "fill_profile"].
                       Use step names from the _JOURNEY_STEP_FIELDS mapping; unknown
                       steps fall back to "default" (all fields).
        environment: Target environment string (test | staging | prod).
        base_url: AUT base URL. Reads BASE_URL env var if empty.
        extra_fields: Optional dict of additional key→value overrides injected into
                      every step's data slice (e.g. {"role": "admin"}).

    Returns:
        JSON string with:
          - ticket_id
          - test_user: full synthetic user profile
          - steps: { step_name: { field: value, ... }, ... }
          - db_seed_queries, cleanup_queries
          - api_mocks
          - pii_masked: true
          - unique_constraints_valid: true
          - output_path: automation/data/<ticket_id>.json
    """
    import os
    from pathlib import Path

    # Generate one synthetic user for the whole journey
    # Call the underlying function directly (the @tool decorator wraps it in a Function object)
    user = json.loads(generate_dynamic_test_user.entrypoint())
    base_url = base_url or os.getenv("BASE_URL", "http://localhost:3000")

    # Build per-step data slices
    steps_data: dict[str, dict] = {}
    for step in journey_steps:
        key = step.lower().replace(" ", "_").replace("-", "_")
        fields = _JOURNEY_STEP_FIELDS.get(key, _JOURNEY_STEP_FIELDS["default"])
        step_slice = {f: user.get(f, "") for f in fields}
        if extra_fields:
            step_slice.update(extra_fields)
        steps_data[step] = step_slice

    unique_id = user["unique_id"]

    result: dict = {
        "ticket_id": ticket_id,
        "test_user": user,
        "steps": steps_data,
        "db_seed_queries": [
            f"INSERT INTO users (username, email, phone, unique_id, created_at) "
            f"VALUES ('{user['username']}', '{user['email']}', '{user['phone']}', '{unique_id}', NOW());"
        ],
        "cleanup_queries": [
            f"DELETE FROM users WHERE unique_id = '{unique_id}';"
        ],
        "api_mocks": {},
        "environment": environment,
        "base_url": base_url,
        "pii_masked": True,
        "unique_constraints_valid": True,
    }

    # Write to automation/data/
    output_dir = Path(__file__).parent.parent.parent / "automation" / "data"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{ticket_id}.json"
    output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    result["output_path"] = str(output_path)

    return json.dumps(result, indent=2)
