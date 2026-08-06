#!/usr/bin/env python
"""UserPromptSubmit hook: classify the prompt and inject a one-line routing card.

Claude Code passes the hook a JSON object on stdin and adds whatever the hook writes
to stdout into the model's context. That is the entire mechanism.

Register in .claude/settings.json (project) or ~/.claude/settings.json (global):

    {
      "hooks": {
        "UserPromptSubmit": [
          { "hooks": [ { "type": "command",
                         "command": "python ~/.claude/hooks/router_hook.py" } ] }
        ]
      }
    }

Write the command as ONE string. Some tooling emits {"command": "python",
"args": ["path.py"]}, and if anything downstream drops `args` you are left with a bare
`python`, which reads the hook payload from stdin and tries to execute it as source.
The failure looks exactly like the hook not firing.

This hook must never break prompt submission, so every failure path is swallowed and
exits 0. Set ROUTER_HOOK_DEBUG=1 to see errors on stderr instead.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _state(cwd):
    """Optional runtime signals. Absent file means 'unknown', and unknown signals hold.

    Write ~/.claude/router/state.json yourself if you want budget gating, e.g.
        {"budget_used_pct": 62, "gpu_free": false}
    """
    for path in (os.path.join(cwd, ".claude", "router", "state.json"),
                 os.path.join(os.path.expanduser("~"), ".claude", "router", "state.json")):
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as handle:
                    return json.load(handle)
            except Exception:
                return {}
    return {}


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0

    prompt = payload.get("prompt") or ""
    cwd = payload.get("cwd") or os.getcwd()

    try:
        import router_brain
        table = router_brain.load_table(cwd)
        decision = router_brain.recommend(prompt, table, _state(cwd))
        if decision:
            print(router_brain.format_card(decision))
    except Exception as exc:
        if os.environ.get("ROUTER_HOOK_DEBUG"):
            print("router_hook: %s" % exc, file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
