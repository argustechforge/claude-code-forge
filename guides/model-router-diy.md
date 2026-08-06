# Build Your Own Model Router for Claude Code

A model router decides *which model, at which reasoning effort, on which provider* should handle a
given piece of work, and then either tells you or dispatches it. This guide describes how to build
one, based on a router that has been running in production across a multi-machine Claude Code setup.

You do not need all of it. The guide is layered, and Level 1 alone recovers most of the benefit for
about twenty minutes of work.

---

## The problem this solves

Claude Code runs your whole session on one model. You pick that model for the hardest thing you
expect to do, which is usually planning or architecture, so you set it high. Then every subagent you
dispatch inherits it.

That is the leak. Planning is expensive on purpose. Implementation usually is not. If you plan on a
top-tier model and then fan out seven implementation subagents without specifying a model, you have
just multiplied your most expensive model across seven tasks that a mid-tier model would have
completed with the same result.

A router fixes three things:

1. Work gets matched to a model that is good enough, instead of the model you happened to be on.
2. Read-heavy work moves off the main conversation, so your context stays clean.
3. You can see the cost shape of a plan before you approve it.

The measurable version of the argument: in one week of logged routing decisions on a real workload,
the classes that got demoted from top-tier to mid-tier showed no drop in task success, while the two
classes that stayed top-tier (architecture planning and final verification) both regressed when
tested at a lower tier. Those two are worth the money. The middle is not.

---

## The shape of a router

Three moving parts, and you can stop after any of them.

```
prompt ──> [1] classifier ──> task class
                                  │
                                  v
                          [2] routing table ──> ordered list of routes
                                                        │
                                                        v
                                                [3] dispatcher ──> advise or run
```

**Classifier.** Turns a prompt into a task class like `implementation_mechanical` or
`architecture_planning`. Regex is enough. You are not trying to be clever, you are trying to be
consistent.

**Routing table.** Maps each class to an ordered list of candidate routes. First route whose
conditions hold, wins. Conditions are things like "usage budget below 90%" or "GPU is free".

**Dispatcher.** Executes the winning route. Some routes it can run itself. Some it can only advise
on, because the harness will not let it act.

---

## Level 1: a policy file, no code

This is the highest value per unit of effort, and it is just text.

Create `~/.claude/model-policy.md` and import it from `~/.claude/CLAUDE.md` with a line reading
`@model-policy.md`. Everything in it applies to every project on the machine.

```markdown
# Model policy

**Never dispatch a subagent without an explicit `model` parameter.** An omitted model inherits the
session model. On a top-tier planning session that multiplies the most expensive model across every
task. Treat a model-less dispatch as a bug.

| Role | Model | Effort |
|------|-------|--------|
| Mechanical task, 1-2 files, complete spec | haiku | low |
| Standard implementation, multi-file integration (default when unsure) | sonnet | high |
| Spec-compliance review | sonnet | high |
| Code-quality review | sonnet | high |
| Security, auth, data-migration or concurrency review | opus | xhigh |
| Re-dispatch after a BLOCKED task, or an architectural judgment call | opus | xhigh |
| Test or build verification gate, single framework | haiku | low |
| Test or build verification gate, multiple frameworks | sonnet | medium |
| Final whole-implementation review | top tier | xhigh |

Planning and final verification run at the top tier. Only the middle drops down.

**Announce the cost shape before starting a fleet of subagents.** One line, e.g. "7 tasks:
5x sonnet + 2x haiku, reviews sonnet, final review opus."
```

That file alone will stop the single most expensive mistake. If you do nothing else, do this.

### Why a table and not a rule

A rule fails the moment the situation drifts from its wording. What you want is a decision
procedure the model can apply to a case you did not anticipate. The table above is really one
sentence: *spend on judgment, not on typing.* Planning, architecture and final verification are
judgment. Writing a file to a complete spec is typing.

---

## Level 2: a routing table plus a skill

Level 1 is advice the model may or may not apply. Level 2 makes it queryable and consistent.

### The table

Store it as JSON so both a script and the model can read it. `~/.claude/router/router-table.json`:

```json
{
  "version": 1,
  "providers": {
    "anthropic": { "enabled": true },
    "local":     { "enabled": false, "endpoint": "http://localhost:1234/v1" }
  },
  "autonomy": {
    "mode": "hybrid",
    "auto_dispatch_classes": [
      "research_locate",
      "research_review",
      "summarization",
      "bulk_data_processing",
      "investigation_diagnosis"
    ]
  },
  "task_classes": {
    "architecture_planning": {
      "routes": [
        { "provider": "anthropic", "model": "opus",   "effort": "xhigh",  "via": "main-session",
          "when": { "budget_below": 90 } },
        { "provider": "anthropic", "model": "sonnet", "effort": "xhigh",  "via": "main-session" }
      ]
    },
    "final_review": {
      "routes": [
        { "provider": "anthropic", "model": "opus",   "effort": "xhigh",  "via": "subagent",
          "when": { "budget_below": 95 } },
        { "provider": "anthropic", "model": "sonnet", "effort": "xhigh",  "via": "subagent" }
      ]
    },
    "implementation_standard": {
      "routes": [
        { "provider": "anthropic", "model": "sonnet", "effort": "high",   "via": "subagent" }
      ]
    },
    "implementation_mechanical": {
      "routes": [
        { "provider": "anthropic", "model": "haiku",  "effort": "low",    "via": "subagent" }
      ]
    },
    "routine_review": {
      "routes": [
        { "provider": "anthropic", "model": "sonnet", "effort": "high",   "via": "subagent" }
      ]
    },
    "research_locate": {
      "routes": [
        { "provider": "anthropic", "model": "haiku",  "effort": "medium", "via": "subagent" }
      ]
    },
    "summarization": {
      "routes": [
        { "provider": "anthropic", "model": "haiku",  "effort": "medium", "via": "subagent" }
      ]
    },
    "bulk_data_processing": {
      "routes": [
        { "provider": "anthropic", "model": "haiku",  "effort": "low",    "via": "subagent" }
      ]
    },
    "investigation_diagnosis": {
      "routes": [
        { "provider": "anthropic", "model": "sonnet", "effort": "high",   "via": "subagent" }
      ]
    },
    "long_context_analysis": {
      "routes": [
        { "provider": "anthropic", "model": "sonnet", "effort": "medium", "via": "main-session" }
      ]
    }
  }
}
```

Start with those ten classes. The production table has nineteen, and the extra nine are all
provider-specific escapes (image generation, location lookup, web research) that only pay off once
you have more than one provider wired up.

### The `via` field is the important one

`via` says *how* the route can be executed, and getting this wrong is the most common way a router
starts lying to you.

| `via` | Meaning | What the model may do |
|-------|---------|-----------------------|
| `main-session` | The route needs the main conversation to be on a different model | **Advise only.** Print the exact `/model X` and `/effort Y` commands. Never claim to have switched the session model, because it cannot. |
| `subagent` | Dispatch through the Agent/Task tool | Dispatch with an explicit `model` parameter. |
| `cli` | Shell out to another vendor's CLI | Run it, capture stdout, relay the result. |
| `api` | Direct HTTP call, e.g. a local server | Call it, relay the result. |
| `web` | A browser-only destination | Advise only. Give the link. |

The `main-session` distinction matters because a model that says "switching to Opus now" and then
carries on as Sonnet has produced a confidently wrong status report, and nothing downstream will
catch it.

### The skill

Add `~/.claude/skills/model-router/SKILL.md` so the model knows when and how to consult the table.
Keep the frontmatter `description` specific, because that string is what triggers the skill.

```markdown
---
name: model-router
description: Pick the best model, effort and provider for a task. Use when a new task starts, when
  the user asks which model to use, when the user wants to save usage on an expensive model, or
  when work should be sent to a local model or another vendor's CLI.
effort: low
---

# Model router

1. Classify the task against `~/.claude/router/router-table.json`. If nothing matches, stop and say
   so. An unclassified task is not an error, it just means route manually.
2. Walk the class's `routes` in order. Take the first whose `when` conditions all hold. If a route
   has no `when`, it always holds, so put your safe fallback last.
3. Execute by `via`, using the table above. Advisory routes are advisory.
4. If the class is listed in `autonomy.auto_dispatch_classes`, dispatch without asking. Otherwise
   present the choice, recommended option first, and accept a one-key confirmation.
5. On dispatch failure, fall through to the next route and say that you did.
```

---

## Level 3: a hook that classifies every prompt

At Level 2 the router only runs when someone remembers to invoke it. Level 3 makes it automatic by
classifying on every prompt submission and injecting a suggestion into context.

Claude Code fires `UserPromptSubmit` hooks before the model sees the prompt, and anything the hook
prints on stdout is added to the model's context. That is the whole mechanism.

`~/.claude/settings.json`:

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          { "type": "command", "command": "python ~/.claude/hooks/router_hook.py" }
        ]
      }
    ]
  }
}
```

> **Gotcha.** Write the hook as a single `command` string. Some tooling emits
> `{"command": "python", "args": ["path.py"]}`, and if anything downstream drops `args` you are left
> with a bare `python`, which reads the payload from stdin and executes it as source. It fails in a
> way that looks like the hook simply not firing.

The classifier itself is regex over the prompt text. Order matters, because the first match wins, so
put narrow patterns above broad ones:

```python
import json, os, re, sys

CLASS_PATTERNS = [
    ("final_review", r"\bfinal (review|verification)\b|\bsecurity (audit|review)\b"
                     r"|\bpre.?(merge|ship|deploy) review\b"),
    ("architecture_planning",
        r"\b(design|architect|restructur\w+|scaffold)\b.*"
        r"\b(system|feature|module|app|project|approach|structure|pipeline)\b"
        r"|\bbrainstorm\b|\b(implementation|migration) plan\b|\bwrite (the |a )?(spec|plan)\b"
        r"|\bwhat.?s the best (way|approach|option)\b|\btrade.?offs?\b"),
    ("routine_review", r"\breview\b.*\b(code|spec|pr|diff|change|implementation)s?\b"),
    ("investigation_diagnosis",
        r"\b(debug|diagnose|troubleshoot|root.?cause)\b"
        r"|\bwhy\b.*\b(is|are|isn.?t|does|doesn.?t|won.?t|can.?t|not)\b"
        r"|\b(not working|doesn.?t work|stopped working)\b"),
    ("research_locate", r"\b(find|locate|where is|which file|search for)\b"),
    ("summarization", r"\bsummari[sz]e\b|\btl.?dr\b|\bcondense\b"),
    ("bulk_data_processing", r"\b(for each|across all|every file|bulk|batch)\b"),
    ("implementation_mechanical", r"\b(rename|move|delete|add a field|bump|update the version)\b"),
    ("implementation_standard", r"\b(implement|build|write|add|create|fix|refactor)\b"),
]

ACK = re.compile(r"^(ok|okay|thanks|thank you|yes|no|sure|got it|nice|cool)\b[.! ]*$", re.I)

def classify(prompt):
    text = (prompt or "").strip()
    if len(text) < 12 or ACK.match(text):
        return None
    for cls, pat in CLASS_PATTERNS:
        if re.search(pat, text, re.I):
            return cls
    return None

payload = json.load(sys.stdin)
cls = classify(payload.get("prompt", ""))
if cls:
    table = json.load(open(os.path.expanduser("~/.claude/router/router-table.json")))
    route = table["task_classes"][cls]["routes"][0]
    auto = cls in table["autonomy"]["auto_dispatch_classes"]
    label = "auto-dispatch" if auto else "suggestion"
    print(f"[Route: {label}] {cls} -> {route['provider']}:{route.get('model')} "
          f"effort={route.get('effort')} via {route['via']}")
```

### The single most important lesson from running this

The first version injected an opt-in card: *"press r to route."* Over one week it was shown **667
times and accepted 0 times.** Not "rarely." Zero.

Opt-in routing is dead on arrival, because accepting a route costs a keystroke and a context switch
at the exact moment you are trying to think about something else. Nobody pays that.

The fix was to split the classes in two. Read-heavy classes where delegation is almost always
correct (locating code, summarizing, bulk processing, diagnosing) became **auto-dispatch**: the card
is an instruction, not an offer, and the model fans them out to subagents without asking. Everything
that changes code stayed opt-in, because you want to be in the loop when something is about to be
edited.

If you build Level 3, build the auto-dispatch split with it. An opt-in-only router is a card you
will learn to ignore.

---

## Verification, which is where routers usually lie to you

Two failure modes are worth designing against up front.

**A model pin that silently did not apply.** If you route work to another vendor's CLI with a
model flag and the flag is unsupported, most CLIs fall back to a default and exit 0. Confirm the pin
from the tool's own session or configuration output, never by inference from how long it took.
Latency correlates with load, not with model identity. A whole benchmark run was invalidated this
way, because the pins had never applied and every row measured the same default model.

**A route that "worked" because it never ran.** Log every decision, including the ones you
overrode and the ones you ignored, then read the log weekly:

```
python ~/.claude/hooks/router_cli.py log \
  --task-class implementation_standard \
  --action accepted|overridden|ignored \
  --recommended "sonnet/high" --chosen "sonnet/high" --via subagent
```

The acceptance rate per class is the signal that tells you which entries in the table are wrong. A
class you override every time is misclassified or mis-tiered. A class you accept every time is a
candidate for auto-dispatch.

---

## Before you reach for a bigger model

Routing pressure usually shows up as "the output is not good enough, use a better model." That
instinct is wrong most of the time. On four production quality problems, three turned out to be a
transport artifact, a wiring mistake, and a missing prompt rule. One was actually the model.

The decisive test costs almost nothing: **run the failing case on a cheap model and an expensive
one. If both fail the same way, it is the prompt, not the model.**

In one case a sixty-word grounding rule took a small fast model from failing every hallucination
case to passing all eight, while a flagship model at high effort still failed the same case without
it. The cheap model with the right prompt beat the expensive model without it. Escalating would have
cost more and fixed less.

Put the layer check in front of the router, not behind it: data and context, then prompt, then
wiring, then transport, then model. Cheapest first.

---

## What to build, in order

1. The Level 1 policy file. Twenty minutes, and it stops the expensive mistake.
2. The routing table, once you notice yourself making the same tier call repeatedly.
3. The skill, once the table is stable enough that you want it consulted rather than remembered.
4. The hook, once you are confident about which classes are safe to auto-dispatch.

Do not start at Level 3. A classifier you do not trust yet, wired to automatic dispatch, will send
work to the wrong model faster than you can notice.
