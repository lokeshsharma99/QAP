"""Patch agno/utils/team.py to guard against None run_response."""

path = "/usr/local/lib/python3.12/site-packages/agno/utils/team.py"

with open(path, "r") as f:
    content = f.read()

old_lines = (
    '        for interaction in member_responses:\n'
    '            response_dict = interaction["run_response"].to_dict()\n'
)
new_lines = (
    '        for interaction in member_responses:\n'
    '            _run_resp = interaction.get("run_response")\n'
    '            if _run_resp is None:\n'
    '                continue  # Guard: member run was blocked or failed without a RunOutput\n'
    '            response_dict = _run_resp.to_dict()\n'
)

if old_lines not in content:
    print("ERROR: target pattern not found in file — already patched or version mismatch")
    exit(1)

patched = content.replace(old_lines, new_lines, 1)

with open(path, "w") as f:
    f.write(patched)

print("agno/utils/team.py patched successfully")
