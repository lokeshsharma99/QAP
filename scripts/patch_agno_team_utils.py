"""Patch agno/utils/team.py to guard against None run_response."""

path = "/usr/local/lib/python3.12/site-packages/agno/utils/team.py"

with open(path, "r") as f:
    content = f.read()

patches = [
    # Patch 1: guard to_dict() call in get_team_member_interactions_str
    (
        '        for interaction in member_responses:\n'
        '            response_dict = interaction["run_response"].to_dict()\n',
        '        for interaction in member_responses:\n'
        '            _run_resp = interaction.get("run_response")\n'
        '            if _run_resp is None:\n'
        '                continue  # Guard: member run was blocked or failed without a RunOutput\n'
        '            response_dict = _run_resp.to_dict()\n',
    ),
    # Patch 2: guard .images access in get_team_run_context_images
    (
        '        for interaction in member_responses:\n'
        '            if interaction["run_response"].images:\n'
        '                images.extend(interaction["run_response"].images)\n',
        '        for interaction in member_responses:\n'
        '            _run_resp_img = interaction.get("run_response")\n'
        '            if _run_resp_img is not None and _run_resp_img.images:\n'
        '                images.extend(_run_resp_img.images)\n',
    ),
    # Patch 3: guard .videos access in get_team_run_context_videos
    (
        '        for interaction in member_responses:\n'
        '            if interaction["run_response"].videos:\n'
        '                videos.extend(interaction["run_response"].videos)\n',
        '        for interaction in member_responses:\n'
        '            _run_resp_vid = interaction.get("run_response")\n'
        '            if _run_resp_vid is not None and _run_resp_vid.videos:\n'
        '                videos.extend(_run_resp_vid.videos)\n',
    ),
    # Patch 4: guard .audio access in get_team_run_context_audio
    (
        '        for interaction in member_responses:\n'
        '            if interaction["run_response"].audio:\n'
        '                audio.extend(interaction["run_response"].audio)\n',
        '        for interaction in member_responses:\n'
        '            _run_resp_aud = interaction.get("run_response")\n'
        '            if _run_resp_aud is not None and _run_resp_aud.audio:\n'
        '                audio.extend(_run_resp_aud.audio)\n',
    ),
]

applied = 0
for old, new in patches:
    if old in content:
        content = content.replace(old, new, 1)
        applied += 1
    else:
        print(f"WARNING: patch pattern not found (already applied or version mismatch):\n  {old[:80]!r}")

with open(path, "w") as f:
    f.write(content)

print(f"agno/utils/team.py patched successfully ({applied}/{len(patches)} patches applied)")
