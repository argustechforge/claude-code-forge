---
name: model-router
description: Pick the model, reasoning effort and provider for a task, then advise or dispatch. Use when a [Route] card appears in context and the user accepts it, when a new task starts and the model tier is not obvious, when the user asks which model should handle something, when they want to conserve usage on an expensive model, or when work should go to a local model or another vendor's CLI.
when_to_use: "a [Route] card is present; 'route this'; 'which model should handle this'; 'save my usage'; 'run this on the local model'"
effort: low
---

# Model router

Advisory for the main session. Enforcing for anything dispatched.

## Flow

1. **Get the decision.** If a `[Route]` card is already in recent context, use it. Otherwise run:

   ```bash
   python .claude/hooks/router_cli.py recommend "<task text>" --json
   ```

   Falls back to `~/.claude/hooks/router_cli.py` when the project has no local copy.

2. **If nothing classifies, say so and stop.** An unclassified prompt is not an error. It means
   route by hand. Do not invent a class to fill the gap.

3. **Act on the card type.**

   | Card | Meaning |
   |------|---------|
   | `[Route: auto-dispatch]` | An instruction, not an offer. Dispatch it without asking, splitting into parallel subagents when the work divides cleanly. Skip only if the task is trivial or the user asked to stay inline. |
   | `[Route: advisory]` | Print the exact commands and why. Do not act. |
   | `[Route]` | Present the option, recommended first, one-key accept. |

4. **Execute by `via`.**

   - `main-session` is **advisory only**. Give the user the literal `/model X` then `/effort Y`
     commands. **Never say you switched the session model.** You cannot, and a false status report
     here is invisible to everything downstream.
   - `subagent` dispatches through the Agent tool with an **explicit `model` parameter**. An omitted
     model inherits the session model, which is the whole failure this router exists to prevent.
     State the model and effort in the dispatch line.
   - `cli` shells out to the named tool. Confirm the model pin from the tool's own session or config
     output, never from how long it took. Latency tracks load, not model identity.
   - `api` posts to the configured endpoint and relays the result.
   - `web` is advisory. Give the link.

5. **Log every decision, including the ones you did not take.**

   ```bash
   python .claude/hooks/router_cli.py log --task-class <cls> \
     --action accepted|overridden|ignored \
     --recommended "<label>" --chosen "<label>" --via <via>
   ```

   Logging only the accepts makes the report measure agreement with itself.

6. **On dispatch failure**, fall through to the next route in the class and say that you did.

## Sub-commands

| Command | Does |
|---------|------|
| `router_cli.py classify "<text>"` | Task class only |
| `router_cli.py recommend "<text>" [--json]` | Full routing decision |
| `router_cli.py table` | Active classes, auto-dispatch flags, first reachable route |
| `router_cli.py report` | Acceptance rate per class, with a re-tier verdict |
| `router_cli.py doctor` | Table resolution, unreachable routes, classifier self-test |

## Reading the report

Acceptance rate per class is the only real feedback loop here.

- **90% or higher**, and the class is a candidate for `auto_dispatch_classes`, provided it is
  read-heavy. Never auto-dispatch a class that edits code.
- **Under 40%**, and the table row is wrong. Either the class is mis-tiered or the pattern is
  catching prompts it should not.
- **Under five decisions**, and there is nothing to conclude. Wait.

## Before you route to a bigger model

Poor output reads like a model problem and usually is not. Check the cheap layers first: data and
context, then prompt, then wiring, then transport, then model.

The decisive test costs one extra run. **Run the failing case on a cheap model and an expensive one.
If both fail the same way, it is the prompt, not the model.** Escalating a prompt problem costs more
and fixes nothing.
