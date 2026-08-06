# ModelRouter

A working, simplified model router for Claude Code. Classifies each prompt, picks a model, effort
and provider from a table you control, and either dispatches the work or tells you what to run.

Everything under `.claude/` here mirrors the layout it needs in a real setup, so installing is a
copy. No build step, no dependencies, standard-library Python only.

This is the runnable companion to [../guides/model-router-diy.md](../guides/model-router-diy.md),
which explains why each piece is shaped the way it is. Read that if you want to build your own
rather than take this one.

## Layout

```
ModelRouter/
└── .claude/
    ├── router/
    │   └── router-table.json          the routing table, 10 task classes
    ├── hooks/
    │   ├── router_brain.py            classification + route selection (no side effects)
    │   ├── router_hook.py             UserPromptSubmit hook, injects the route card
    │   └── router_cli.py              classify / recommend / log / report / table / doctor
    ├── skills/
    │   └── model-router/SKILL.md      tells the model how to act on a card
    └── settings.json.example          hook registration to merge into your settings.json
```

## Install

Pick one scope. The router checks the project path first and falls back to the home path, so a
project copy overrides a global one per file.

**Globally**, for every project on the machine:

```bash
cp -r ModelRouter/.claude/router  ~/.claude/
cp -r ModelRouter/.claude/hooks   ~/.claude/
cp -r ModelRouter/.claude/skills  ~/.claude/
```

**Per project**, committed alongside the code:

```bash
cp -r ModelRouter/.claude/. /path/to/project/.claude/
```

Then merge the `hooks` block from `settings.json.example` into `~/.claude/settings.json` (global) or
`<project>/.claude/settings.json` (project). Merge it, do not overwrite the file.

On Windows, use the full path rather than `~`, and `python` rather than `python3`:

```json
{ "type": "command", "command": "python C:/Users/YOU/.claude/hooks/router_hook.py" }
```

Confirm it works:

```bash
python ~/.claude/hooks/router_cli.py doctor
```

That prints the table search path, the table it actually loaded, any task class with no reachable
route, and a 21-case classifier self-test. Expect `doctor: OK`.

## What you get

Start a session and type something. The hook classifies it and injects one line the model reads.

```
[Route: auto-dispatch] research_locate -> anthropic:haiku effort=medium via subagent. Dispatch
this without asking; the work is read-heavy and belongs off the main conversation.

[Route: advisory] architecture_planning -> anthropic:opus effort=xhigh via main-session. Tell the
user the commands; do not claim to have switched the session model.

[Route] implementation_standard -> anthropic:sonnet effort=high via subagent. Press r to route,
or continue as-is.
```

Three card types, and the difference between them is the point.

**Auto-dispatch** is an instruction. Those classes are read-heavy, so a wrong call wastes a subagent
and nothing more. Getting that work off the main conversation is worth more than confirming it.

**Advisory** never claims to have acted. Nothing in the harness lets a hook or skill change the
model the main session runs on. A card that said "switched to Opus" would be a confidently wrong
status report, and nothing downstream would catch it.

**Opt-in** is everything that edits code. You stay in the loop where being wrong costs a commit.

Prompts that are not tasks produce no card at all. `ok thanks` is silent, which is what keeps the
cards worth reading.

## The table

`.claude/router/router-table.json`. Each class holds an ordered list of routes, and the first one
whose `when` conditions hold wins.

```json
"final_review": {
  "difficulty": "hard",
  "routes": [
    { "provider": "anthropic", "model": "opus",   "effort": "xhigh", "via": "subagent",
      "when": { "budget_below": 95 } },
    { "provider": "anthropic", "model": "sonnet", "effort": "xhigh", "via": "subagent" }
  ]
}
```

**Always end a class with an unconditional route.** A route with no `when` always holds, so it is
your fallback. `doctor` fails loudly if a class can become unreachable.

`via` decides what the model is allowed to do with the route:

| `via` | The model may |
|-------|---------------|
| `main-session` | Advise only. Print the `/model` and `/effort` commands. |
| `subagent` | Dispatch, with an explicit `model` parameter. |
| `cli` | Shell out, then confirm the model pin from the tool's own output. |
| `api` | Call the endpoint and relay the result. |
| `web` | Advise only. Give the link. |

### Budget gating

Conditions read an optional `state.json`, which you write yourself:

```json
{ "budget_used_pct": 96, "gpu_free": false }
```

Put it at `.claude/router/state.json` or `~/.claude/router/state.json`. With that file in place,
`final_review` drops from `opus` to `sonnet`, because its gate is 95.

**Unknown signals hold rather than fail.** With no `state.json` every budget-gated route stays
eligible. The alternative is worse: a missing file would silently skip every gated route and always
take the cheap fallback, which looks identical to the router working while it is actually blind.

## Tuning it

The router is only as good as the table, and the table is wrong at first. `log` and `report` are how
you find out where.

```bash
python .claude/hooks/router_cli.py log --task-class routine_review --action accepted \
  --recommended sonnet/high --chosen sonnet/high --via subagent

python .claude/hooks/router_cli.py report
```

```
task class                    accept overrid ignored   verdict
--------------------------------------------------------------------------
implementation_mechanical          1       4       0   re-tier or re-classify (20%)
research_locate                    6       0       0   consider auto-dispatch (100%)
routine_review                     0       0       1   not enough data (0%)
```

Log the overrides and the ignores too. If you only log the accepts, the report measures agreement
with itself and every row reads 100%.

A class you override almost every time is mis-tiered or the pattern is catching the wrong prompts. A
class you accept almost every time belongs in `auto_dispatch_classes`, as long as it is read-heavy.
Never auto-dispatch a class that edits code.

## Adding a task class

1. Add a pattern to `CLASS_PATTERNS` in `router_brain.py`. Order matters, first match wins, so
   narrow patterns go above broad ones. `implementation_standard` sits last on purpose, because its
   verbs show up inside prompts that are really something else.
2. Add a case to `_CASES` in the same file, including one prompt that should *not* match it.
3. Add the class to `router-table.json` with at least one unconditional route.
4. Run `python .claude/hooks/router_cli.py doctor`.

## What this leaves out

The production version this was cut down from carries nineteen classes, several providers, GPU
probing for a local model fleet, per-provider quota ledgers, and graduated autonomy that promotes
classes to auto-dispatch on measured evidence. None of that helps until you have more than one
provider wired up and a few weeks of logged decisions.

What is here is the part that pays immediately: consistent classification, an explicit table, the
advisory-versus-dispatch distinction, and a feedback loop that tells you which rows are wrong.

## Verified

Against Python 3 on Windows, from this directory:

```
doctor: OK                          table resolution, reachability, 21/21 classifier self-test
hook cards                          auto-dispatch, advisory and opt-in all render correctly
non-task prompts                    "ok thanks" produces no output
malformed stdin                     exits 0 without a traceback, never blocks prompt submission
budget gating                       state.json at 96% drops final_review from opus to sonnet
project-over-global                 local table wins when both exist
report verdicts                     re-tier at 20%, auto-dispatch at 100%, held below 5 samples
```
