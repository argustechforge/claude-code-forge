#!/usr/bin/env python
"""Command line front end for the simplified model router.

    python router_cli.py classify  "why is the build failing?"
    python router_cli.py recommend "review this diff" [--json]
    python router_cli.py log --task-class routine_review --action accepted \
                             --recommended sonnet/high --chosen sonnet/high --via subagent
    python router_cli.py report
    python router_cli.py table
    python router_cli.py doctor

`log` and `report` are the pair that matter over time. The acceptance rate per class is
the signal that tells you which rows of the table are wrong: a class you override every
time is mis-tiered, and a class you accept every time is a candidate for auto-dispatch.
Log the overrides and the ignores too, or the rate only ever measures agreement.
"""

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import router_brain  # noqa: E402


def _decisions_path(cwd=None):
    cwd = cwd or os.getcwd()
    local = os.path.join(cwd, ".claude", "router")
    if os.path.isdir(local):
        return os.path.join(local, "decisions.jsonl")
    home = os.path.join(os.path.expanduser("~"), ".claude", "router")
    os.makedirs(home, exist_ok=True)
    return os.path.join(home, "decisions.jsonl")


def _route_label(route):
    target = route.get("model") or route.get("tier") or route.get("provider")
    return "%s/%s" % (target, route.get("effort")) if route.get("effort") else str(target)


def cmd_classify(args):
    cls = router_brain.classify_task(args.prompt)
    print(cls if cls else "(unclassified: not a routable task)")
    return 0


def cmd_recommend(args):
    table = router_brain.load_table()
    decision = router_brain.recommend(args.prompt, table, {})
    if not decision:
        print("(unclassified: route manually)")
        return 0
    if args.json:
        decision.pop("rejected", None)
        print(json.dumps(decision, indent=2))
    else:
        print(router_brain.format_card(decision))
    return 0


def cmd_log(args):
    record = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "task_class": args.task_class,
        "action": args.action,
        "recommended": args.recommended,
        "chosen": args.chosen,
        "via": args.via,
    }
    path = _decisions_path()
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")
    print("logged -> %s" % path)
    return 0


def cmd_report(args):
    path = _decisions_path()
    if not os.path.isfile(path):
        print("no decisions logged yet (%s)" % path)
        return 0

    stats = defaultdict(lambda: defaultdict(int))
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            stats[rec.get("task_class", "?")][rec.get("action", "?")] += 1

    print("%-28s %7s %7s %7s   %s" % ("task class", "accept", "overrid", "ignored", "verdict"))
    print("-" * 74)
    for cls in sorted(stats):
        row = stats[cls]
        acc, ovr, ign = row["accepted"], row["overridden"], row["ignored"]
        total = acc + ovr + ign
        rate = (100.0 * acc / total) if total else 0.0
        if total < 5:
            verdict = "not enough data"
        elif rate >= 90:
            verdict = "consider auto-dispatch"
        elif rate < 40:
            verdict = "re-tier or re-classify"
        else:
            verdict = "keep as opt-in"
        print("%-28s %7d %7d %7d   %s (%.0f%%)" % (cls, acc, ovr, ign, verdict, rate))
    return 0


def cmd_table(args):
    table = router_brain.load_table()
    auto = set((table.get("autonomy") or {}).get("auto_dispatch_classes") or [])
    print("source: %s\n" % table.get("_source"))
    print("%-28s %-6s %-8s %s" % ("task class", "auto", "diff", "first route"))
    print("-" * 74)
    for cls, entry in table.get("task_classes", {}).items():
        route, _ = router_brain.select_route(cls, table, {})
        label = "%s %s" % (_route_label(route), "[%s]" % route.get("via")) if route else "(none)"
        print("%-28s %-6s %-8s %s" % (cls, "yes" if cls in auto else "-",
                                      entry.get("difficulty", "medium"), label))
    return 0


def cmd_doctor(args):
    ok = True
    print("table search path:")
    for path in router_brain.table_paths():
        mark = "found" if os.path.isfile(path) else "missing"
        print("  [%s] %s" % (mark, path))
    try:
        table = router_brain.load_table()
        print("loaded: %s (%d classes)" % (table.get("_source"),
                                           len(table.get("task_classes", {}))))
    except Exception as exc:
        print("ERROR: %s" % exc)
        return 1

    for cls in table.get("task_classes", {}):
        route, rejected = router_brain.select_route(cls, table, {})
        if route is None:
            print("ERROR: %s has no reachable route (all %d rejected). Add an "
                  "unconditional fallback last." % (cls, len(rejected)))
            ok = False

    failures = router_brain.self_test()
    if failures:
        ok = False
    print("doctor: %s" % ("OK" if ok else "problems found"))
    return 0 if ok else 1


def main():
    parser = argparse.ArgumentParser(description="Simplified model router")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("classify"); p.add_argument("prompt"); p.set_defaults(fn=cmd_classify)
    p = sub.add_parser("recommend"); p.add_argument("prompt")
    p.add_argument("--json", action="store_true"); p.set_defaults(fn=cmd_recommend)

    p = sub.add_parser("log")
    p.add_argument("--task-class", required=True)
    p.add_argument("--action", required=True, choices=["accepted", "overridden", "ignored"])
    p.add_argument("--recommended", default=""); p.add_argument("--chosen", default="")
    p.add_argument("--via", default=""); p.set_defaults(fn=cmd_log)

    sub.add_parser("report").set_defaults(fn=cmd_report)
    sub.add_parser("table").set_defaults(fn=cmd_table)
    sub.add_parser("doctor").set_defaults(fn=cmd_doctor)

    args = parser.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
