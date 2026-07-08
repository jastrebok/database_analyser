#!/usr/bin/env python3

import json
import re
import sys


def main() -> int:
    payload = json.load(sys.stdin)
    tool_input = payload.get("tool_input", {})

    serialized_values = []
    if isinstance(tool_input, dict):
        serialized_values.extend(str(value) for value in tool_input.values())
    else:
        serialized_values.append(json.dumps(tool_input, sort_keys=True))

    needs_confirmation = any(
        re.search(r"(^|[^\w./-])git\s+commit(\s|$)", value, flags=re.IGNORECASE)
        for value in serialized_values
    )

    hook_output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask" if needs_confirmation else "allow",
        }
    }

    if needs_confirmation:
        hook_output["hookSpecificOutput"]["permissionDecisionReason"] = (
            "Confirm before creating a git commit."
        )

    json.dump(hook_output, sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())