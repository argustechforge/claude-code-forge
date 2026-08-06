"""Simplified model router: classification and route selection.

Pure standard library, no dependencies, no side effects. Everything that touches the
filesystem or prints lives in router_hook.py and router_cli.py, so this file stays
importable and testable on its own:

    python router_brain.py --self-test

Table resolution order (first hit wins), which is what makes the router work either
globally or per project:

    <cwd>/.claude/router/router-table.json      project override
    ~/.claude/router/router-table.json          machine default
"""

import json
import os
import re

# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------
# Order matters. First match wins, so narrow patterns go above broad ones.
# implementation_standard is last because its verbs ("add", "fix", "write") appear
# inside plenty of prompts that are really something else.

CLASS_PATTERNS = [
    ("final_review", (
        r"\bfinal (review|verification)\b"
        r"|\bsecurity (audit|review)\b"
        r"|\bpre.?(merge|ship|deploy) review\b"
        r"|\bwhole.implementation review\b"
    )),
    ("architecture_planning", (
        r"\b(design|architect|re.?architect|restructur\w+|consolidat\w+|scaffold)\b.*"
        r"\b(system|feature|module|app|project|approach|structure|layout|pipeline|architecture)\b"
        r"|\bbrainstorm\b"
        r"|\b(implementation|migration) plan\b"
        r"|\bwrite (the |a )?(spec|plan)\b"
        r"|\bwhat.?s the best (way|approach|option|model)\b"
        r"|\bis there (any |a )?better\b"
        r"|\btrade.?offs?\b"
        r"|\bshould(n.?t)? (we|i|it|they)\b"
    )),
    ("routine_review", (
        r"\breview\b.*\b(code|spec|pr|diff|change|implementation|work|task)s?\b"
        r"|\breview (the|this|my|their)\b"
        r"|\badvise on\b"
    )),
    ("investigation_diagnosis", (
        r"\b(debug|diagnose|troubleshoot|root.?cause)\b"
        r"|\b(investigate|look into|figure out|find out)\b.*\b(why|cause|issue|problem|reason)\b"
        r"|\bwhy\b.*\b(is|are|isn.?t|aren.?t|does|doesn.?t|did|didn.?t|won.?t|can.?t|not)\b"
        r"|\bwhat\b.*\b(happened|went wrong|is causing|broke)\b"
        r"|\b(not working|isn.?t working|doesn.?t work|stopped working|no longer works?)\b"
        r"|\b(error|crash|fail(s|ed|ing)?|stuck|hangs?|times? out)\b.*\b(why|what|check|look)\b"
    )),
    ("summarization", (
        r"\bsummari[sz]e\b|\bsummary of\b|\btl.?dr\b|\bcondense\b|\bwrite up (what|the)\b"
    )),
    ("bulk_data_processing", (
        r"\b(for each|across all|every (file|row|record|entry)|bulk|batch|in all \d+)\b"
    )),
    ("research_locate", (
        r"\b(find|locate|where is|where are|which file|search for|grep for|list all)\b"
        r"|\bevery place (we|that|which)\b"
    )),
    ("long_context_analysis", (
        r"\b(read|analy[sz]e|go through|walk through)\b.*\b(whole|entire|all of|full)\b"
        r"|\b(this|the) (transcript|log file|dump|export)\b"
    )),
    ("implementation_mechanical", (
        r"\b(rename|move|delete|remove) (the |this |that )?\w+"
        r"|\badd a (field|column|flag|param|parameter|const|key)\b"
        r"|\b(bump|update) the version\b"
        r"|\bfix the typo\b"
    )),
    ("implementation_standard", (
        r"\b(implement|build|write|add|create|fix|refactor|wire up|hook up|migrate|port)\b"
    )),
]

# Short acknowledgements and chit-chat are not tasks. Without this the router fires a
# card on "ok thanks", which trains you to ignore the cards.
_ACK = re.compile(
    r"^(ok(ay)?|thanks|thank you|ty|yes|yep|no|nope|sure|got it|nice|cool|perfect|great|done)"
    r"\b[.!\s]*$", re.I)
_MIN_CHARS = 12


def classify_task(prompt):
    """Return a task-class string, or None when the prompt is not a routable task."""
    text = (prompt or "").strip()
    if len(text) < _MIN_CHARS or _ACK.match(text):
        return None
    for cls, pattern in CLASS_PATTERNS:
        if re.search(pattern, text, re.I):
            return cls
    return None


# ---------------------------------------------------------------------------
# Table loading
# ---------------------------------------------------------------------------

def table_paths(cwd=None):
    cwd = cwd or os.getcwd()
    return [
        os.path.join(cwd, ".claude", "router", "router-table.json"),
        os.path.join(os.path.expanduser("~"), ".claude", "router", "router-table.json"),
    ]


def load_table(cwd=None):
    """Load the first routing table that exists. Raises FileNotFoundError if none do."""
    tried = table_paths(cwd)
    for path in tried:
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as handle:
                table = json.load(handle)
            table["_source"] = path
            return table
    raise FileNotFoundError("no router-table.json found. Looked in: " + ", ".join(tried))


# ---------------------------------------------------------------------------
# Route selection
# ---------------------------------------------------------------------------

def _provider_enabled(route, table):
    provider = route.get("provider")
    entry = (table.get("providers") or {}).get(provider)
    if entry is None:
        return True          # unknown providers are assumed usable
    return bool(entry.get("enabled", True))


def _when_holds(route, state):
    """Evaluate a route's `when` block.

    Unknown signals hold rather than fail. If usage data is missing we would
    otherwise skip every budget-gated route and silently always take the cheap
    fallback, which looks like the router working while it is actually blind.
    """
    conditions = route.get("when") or {}
    state = state or {}

    budget_cap = conditions.get("budget_below")
    if budget_cap is not None:
        used = state.get("budget_used_pct")
        if used is not None and used >= budget_cap:
            return False

    if "gpu_free" in conditions:
        gpu = state.get("gpu_free")
        if gpu is not None and bool(gpu) != bool(conditions["gpu_free"]):
            return False

    return True


def select_route(task_class, table, state=None):
    """Return (chosen_route, rejected_routes). chosen_route is None if nothing qualifies."""
    entry = (table.get("task_classes") or {}).get(task_class)
    if not entry:
        return None, []

    rejected = []
    for route in entry.get("routes", []):
        if not _provider_enabled(route, table):
            rejected.append((route, "provider disabled"))
            continue
        if not _when_holds(route, state):
            rejected.append((route, "when conditions not met"))
            continue
        return route, rejected
    return None, rejected


def recommend(prompt, table, state=None):
    """Full pipeline: prompt in, routing decision out. None when unclassified."""
    task_class = classify_task(prompt)
    if not task_class:
        return None

    entry = (table.get("task_classes") or {}).get(task_class)
    if not entry:
        return None

    route, rejected = select_route(task_class, table, state)
    if route is None:
        return None

    auto_classes = ((table.get("autonomy") or {}).get("auto_dispatch_classes")) or []
    return {
        "task_class": task_class,
        "difficulty": entry.get("difficulty", "medium"),
        "route": route,
        "auto_dispatch": task_class in auto_classes and route.get("via") == "subagent",
        "advisory": bool(route.get("advisory")) or route.get("via") in ("main-session", "web"),
        "rejected": [{"route": r, "reason": why} for r, why in rejected],
    }


def format_card(decision):
    """One-line context card. This string is what the model actually reads."""
    route = decision["route"]
    target = route.get("model") or route.get("tier") or route.get("provider")
    bits = "%s:%s" % (route.get("provider"), target)
    if route.get("effort"):
        bits += " effort=%s" % route["effort"]

    if decision["auto_dispatch"]:
        return ("[Route: auto-dispatch] %s -> %s via %s. Dispatch this without asking; "
                "the work is read-heavy and belongs off the main conversation."
                % (decision["task_class"], bits, route["via"]))
    if decision["advisory"]:
        return ("[Route: advisory] %s -> %s via %s. Tell the user the commands; "
                "do not claim to have switched the session model."
                % (decision["task_class"], bits, route["via"]))
    return ("[Route] %s -> %s via %s. Press r to route, or continue as-is."
            % (decision["task_class"], bits, route["via"]))


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

_CASES = [
    ("ok thanks", None),
    ("yes", None),
    ("hi", None),
    ("do a final review before we ship", "final_review"),
    ("run a security audit on the auth module", "final_review"),
    ("brainstorm how the plugin system should work", "architecture_planning"),
    ("what's the best approach for the cache layer?", "architecture_planning"),
    ("write a spec for the importer", "architecture_planning"),
    ("review this diff", "routine_review"),
    ("review the code in src/parser", "routine_review"),
    ("why is the build failing?", "investigation_diagnosis"),
    ("the upload stopped working yesterday", "investigation_diagnosis"),
    ("debug the websocket reconnect", "investigation_diagnosis"),
    ("summarize this thread", "summarization"),
    ("for each config file, check the timeout value", "bulk_data_processing"),
    ("find every place we call the parser", "research_locate"),
    ("where is the retry logic defined", "research_locate"),
    ("rename the getUser helper", "implementation_mechanical"),
    ("bump the version to 2.1", "implementation_mechanical"),
    ("implement the retry backoff", "implementation_standard"),
    ("add pagination to the results endpoint", "implementation_standard"),
]


def self_test():
    passed = failed = 0
    for prompt, expected in _CASES:
        got = classify_task(prompt)
        if got == expected:
            passed += 1
        else:
            failed += 1
            print("  FAIL  %-45r expected=%s got=%s" % (prompt, expected, got))
    print("classifier: %d passed, %d failed" % (passed, failed))
    return failed


if __name__ == "__main__":
    import sys
    if "--self-test" in sys.argv:
        sys.exit(1 if self_test() else 0)
    print(__doc__)
