---
description: Review this conversation (or a transcript file) and recommend new skills/commands worth building, then offer to draft one. Genesis only. Never touches an existing tool.
allowed-tools: Read, Glob, Grep, Write
argument-hint: "[--transcript <path>]"
---

# Tool Genesis

Standalone new-tool recommender. No ledger, no scripts, nothing that runs automatically. This
only acts when you run it.

Same procedure as the `tool-genesis` skill, laid out as command steps:

## 1. Resolve input

No `--transcript` flag: use this conversation as already in context.

`--transcript <path>` given: read that file as a Claude Code session transcript (JSONL, one JSON
object per line). Look for `message.content[]` blocks with `type: "tool_use"` (what ran, via
`name` + `input`) and `type: "tool_result"` (`is_error` tells you if it failed), plus the plain
user/assistant text turns. If the path can't be read or doesn't parse, say so in one line and fall
back to the live conversation instead of failing.

Two real gotchas: `message.content` is sometimes a plain string (that's the message text
directly), not always a list of blocks. Handle both. And a real transcript mixes in line types
you don't need (`attachment`, `mode`, `ai-title`, `file-history-snapshot`, etc.). Skip any `type`
you don't recognize rather than enumerating every one.

## 2. Inventory check

`Glob`:
- `.claude/skills/**/SKILL.md`, `.claude/commands/*.md`, `.claude/agents/*.md`
- `~/.claude/skills/*/SKILL.md`, `~/.claude/commands/*.md`, `~/.claude/agents/*.md` (one level
  deep, not `**`: a real `~/.claude` can be large enough that a deep recursive glob is slow or
  hangs)

Read `name` + `description` frontmatter only. An empty, missing, or slow/erroring `.claude` tree
all mean the same thing: treat that side as an empty inventory and keep going. Never let it block
the run.

## 3. Find candidates

Genesis only. Flag a candidate when the inventory doesn't already cover it, AND at least one of:

- the same manual action/pattern recurs 2+ times in what you're reviewing
- one substantial manual workflow happened that's clearly reusable
- the user explicitly asked for something like it

Zero candidates is a valid, expected outcome. Say so plainly rather than forcing a suggestion.

## 4. Report

Numbered list, most-evidenced first. Per candidate: name idea, one line on what it does, proposed
shape (skill/command/hook), and the concrete evidence backing it. Ask which (if any) to build.

## 5. Build (on approval only)

For each accepted candidate: draft the file (`skill` → `.claude/skills/<name>/SKILL.md` with real
frontmatter and a grounded procedure; `command` → `.claude/commands/<name>.md`), show the full
content, and wait for explicit approval before writing it. Never write without that approval.
If Superpowers' `brainstorming` skill looks available, mention it as an alternative fuller path
before drafting, but don't require it.

## Related

| Tool | Difference |
|------|------------|
| `tool-genesis` skill | Same procedure, triggered by natural language instead of the command |

Nothing else in this repo does what this does. It doesn't overlap `ModelRouter`, which handles
model/effort selection, not tool creation.
