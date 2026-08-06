# claude-code-forge

Portable Claude Code toolkit. Skills, agents, hooks and templates that drop into any project and
stay in sync across machines.

The fastest useful thing here is the Level 1 section of
[the model router guide](./guides/model-router-diy.md), one short file that takes about twenty
minutes to adopt and stops the most expensive mistake described below. Everything in the repo is
cut down from a setup [Ted Hayes](https://nutechfusion.com) runs daily on his own machines;
building this kind of system for other people is his business.

Everything here is built to be installed one of two ways:

- **Globally**, by copying into `~/.claude/`, where it applies to every project on the machine.
- **Per project**, by copying into `<project>/.claude/`, where it applies to that project only and
  can be committed alongside the code.

Nothing depends on a particular machine, and nothing requires editing a plugin's own files.

## What is here

| | What it is |
|---|---|
| **[ModelRouter/](./ModelRouter/)** | A working simplified model router. Copy `ModelRouter/.claude/` into `~/.claude/` or a project's `.claude/` and it runs. Standard-library Python, no dependencies. |
| [guides/model-router-diy.md](./guides/model-router-diy.md) | How to build a router yourself, in four levels, from a twenty-minute policy file up to a hook that classifies every prompt. The reasoning behind ModelRouter. |
| [guides/superpowers-augments-full.md](./guides/superpowers-augments-full.md) | The complete set of changes to the Superpowers brainstorming flow: no phase gates, better question formatting, subagent-driven handoff, model policy. |
| [guides/superpowers-augments-router-only.md](./guides/superpowers-augments-router-only.md) | Just the part that assigns models to implementation subagents. A strict subset of the full set. |
| [presentations/](./presentations/) | Talks built on this tooling. Slides, PDF and PNG exports, one folder per session. |

If you want the thing running today, install [ModelRouter](./ModelRouter/).

## Why this exists

Claude Code runs a session on one model, and subagents inherit it unless you say otherwise. You pick
the session model for the hardest thing you expect to do, so it is usually set high. Then a plan
fans out seven implementation subagents and every one of them runs on your most expensive model to
do work a mid-tier model would have finished identically.

Most of what is collected here comes back to that: decide once where judgment is actually needed,
write the decision down where the model will read it, and stop paying judgment prices for typing.

The guidance is drawn from a setup that has been running across several machines, and the
non-obvious parts are the ones that came from something going wrong. Those are called out where they
appear.

## Status

Early. The guides and the ModelRouter drop-in are here. More tooling to follow.

## Where to go from here

Read the Level 1 section of [the model router guide](./guides/model-router-diy.md) and write the
policy file. It takes about twenty minutes and it stops the most expensive habit this repo
describes. If that earns its keep, [ModelRouter](./ModelRouter/) is the next step up: copy one
folder and run `doctor`.

If something here breaks against your setup, open an issue. The useful parts of these guides came
from things going wrong, and a new failure report improves them more than a star does. See
[CONTRIBUTING.md](./CONTRIBUTING.md) for what is worth reporting.

Everything in this repo is cut down from a setup Ted Hayes runs on his own machines around the
clock. Building custom AI tooling for other people is his business at
[nutechfusion.com](https://nutechfusion.com). If you'd rather hand this class of problem to someone
who has already hit the failure modes, start there.
