# claude-code-forge

Portable Claude Code toolkit. Skills, agents, hooks and templates that drop into any project and
stay in sync across machines.

Everything here is built to be installed one of two ways:

- **Globally**, by copying into `~/.claude/`, where it applies to every project on the machine.
- **Per project**, by copying into `<project>/.claude/`, where it applies to that project only and
  can be committed alongside the code.

Nothing depends on a particular machine, and nothing requires editing a plugin's own files.

## Guides

| Guide | What it covers |
|-------|----------------|
| [Build your own model router](./guides/model-router-diy.md) | Routing work to the right model, effort and provider. Four levels, from a twenty-minute policy file up to a hook that classifies every prompt. |
| [Superpowers augments, full set](./guides/superpowers-augments-full.md) | The complete set of changes to the Superpowers brainstorming flow: no phase gates, better question formatting, subagent-driven handoff, model policy. |
| [Superpowers augments, routing only](./guides/superpowers-augments-router-only.md) | Just the part that assigns models to implementation subagents. A strict subset of the full set. |

If you are starting from scratch and only have twenty minutes, read the Level 1 section of the model
router guide. It is a single text file, and it prevents the most expensive mistake in the list.

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

Early. The guides are here. The drop-in `.claude/` payload is next.
