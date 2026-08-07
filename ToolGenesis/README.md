# ToolGenesis

A working, standalone new-tool recommender for Claude Code. Reads a conversation, points out
patterns that would be worth turning into a skill or command, and offers to draft one.

Everything under `.claude/` here mirrors the layout it needs in a real setup, so installing is a
copy. No build step, no dependencies, no code at all beyond two markdown files.

This is a cut-down version of a heavier private system that also audits how existing tools perform
and edits them automatically. None of that shipped here. What's left is the one piece worth having
on its own: point out a recurring pattern and offer to build something for it.

## Layout

```
ToolGenesis/
└── .claude/
    ├── skills/tool-genesis/SKILL.md   natural-language trigger, review procedure
    └── commands/tool-genesis.md       /tool-genesis [--transcript <path>]
```

No hooks, no config file, nothing that runs automatically. It only acts when you ask it to.

## Install

Pick one scope.

**Globally**, for every project on the machine:

```bash
cp -r ToolGenesis/.claude/skills    ~/.claude/
cp -r ToolGenesis/.claude/commands  ~/.claude/
```

**Per project**, committed alongside the code:

```bash
cp -r ToolGenesis/.claude/. /path/to/project/.claude/
```

That's the whole install. No settings.json entry, no hook registration, no restart needed.

## What you get

Ask for it directly, or run the command:

```
/tool-genesis
```

It reads back through the current conversation, checks what's already on your machine so it
doesn't suggest something you have, and reports back:

```
2 candidates worth building, most-evidenced first:

1. `commit-scope-lint` (command)
   You ran the same three-step "check staged files, grep for secrets, confirm branch"
   sequence by hand 4 times this conversation before every commit.

2. `changelog-diff` (skill)
   You pulled the last release's changelog and diffed it against unreleased commits once,
   but it was a real multi-step task and you said "I do this every release."

Build one now? (1/2/both/no)
```

Say no, and nothing happens. Say yes, and it drafts the file, shows you the content, and waits
for you to approve before writing anything.

## How it decides

Genesis only. It never touches an existing tool and it never reports on how one performed. A
candidate only gets suggested if:

- the same manual action or pattern shows up twice or more in the conversation, or
- one substantial manual workflow happened that's clearly reusable, or
- you said something like "I do this every time" or asked for a tool outright,

and only if nothing already installed covers it (it checks your `.claude/skills`, `.claude/commands`
and `.claude/agents`, local and global, before suggesting anything). If nothing clears that bar, it
says so. It does not manufacture a suggestion to have something to show you.

## Reviewing a transcript instead of the live conversation

```
/tool-genesis --transcript ~/.claude/projects/my-project/abc123.jsonl
```

Useful after the fact, or in a fresh session where the conversation you want reviewed already
ended. A missing or unreadable path falls back to the live conversation with a note, rather than
failing outright.

## What this leaves out

The private system this was cut down from also tracks how every tool performed across every
session (errors, retries, wrong model for the job, a tool that should have fired and didn't),
keeps a confidence ledger that accumulates evidence across every project on the machine before
auto-applying a fix, and aggregates that ledger across a whole fleet of machines. None of that is
here.

What's here is the one piece that's useful standalone: read a conversation, notice something worth
building, offer to build it. No ledger, no scripts, no cache file, nothing that runs on its own.

## Verified

Run for real against a real 940KB session transcript, 2026-08-06: the session that designed this
tool, reviewed with `--transcript` from a second, independent Claude Code instance.

```
candidate quality      2 evidence-backed candidates, one correctly flagged as borderline (2 occurrences)
duplicate check         found this repo's ModelRouter in inventory, did not suggest touching it
self-reference          did not suggest "build ToolGenesis" even though the transcript was
                        literally that conversation. Already in inventory, correctly silent
global inventory glob   FAILED on the first pass: a single recursive ~/.claude/** glob timed out
                        on a real home directory. Fixed: global glob is now one level deep and
                        an explicit instruction says a slow/erroring scan degrades like a missing
                        one, same as the project-local empty-tree case.
transcript parsing      FAILED on the first pass: real user turns are often a plain string, not
                        always the array-of-blocks the schema example showed. Fixed: content is
                        now documented as "string or list, handle both," plus a note that a real
                        transcript carries line types (attachment, mode, ai-title, ...) this tool
                        doesn't need and should skip rather than enumerate.
```

Both failures above were caught by actually running it against a real transcript before writing
this section, not by reasoning about the instructions in the abstract. The fixes are already
reflected in `SKILL.md` and `tool-genesis.md`.
