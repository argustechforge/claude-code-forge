---
name: tool-genesis
description: Review the current conversation (or a given transcript file) and recommend new skills/commands worth building from patterns in it, then offer to draft one. Genesis only. Never audits or edits an existing tool. Use when the user asks what tools should be built from this chat, whether something here is worth automating, or invokes /tool-genesis directly.
when_to_use: "'what tools should we build from this'; 'is this worth automating'; 'any new tools worth making here'; a /tool-genesis invocation"
effort: medium
---

# Tool genesis

Recommend new tools from evidence in a conversation. Nothing else. Never proposes a change to a
tool that already exists. That's a different job this skill doesn't do.

## 1. Resolve the input

- Default: the current conversation, as already in context.
- If invoked with `--transcript <path>`: read that file instead. It's a Claude Code session
  transcript, JSONL, one JSON object per line. Real entries look like:
  ```json
  {"type": "assistant", "message": {"role": "assistant", "content": [
    {"type": "tool_use", "name": "Bash", "input": {"command": "..."}}
  ]}}
  ```
  and
  ```json
  {"type": "user", "message": {"role": "user", "content": [
    {"type": "tool_result", "tool_use_id": "...", "is_error": false, "content": "..."}
  ]}}
  ```
  Walk the `message.content[]` blocks for `tool_use` (what ran) and `tool_result` (whether it
  errored) to reconstruct what happened, plus the plain-text user/assistant turns for context and
  explicit asks. Two real gotchas:
  - `message.content` is **not always a list of blocks**: a plain user turn is often just a
    string. If it's a string, that string *is* the message text. If it's a list, walk it for
    `text` / `tool_use` / `tool_result` blocks as above. Handle both.
  - A real transcript mixes in line types this skill doesn't need, like `attachment`, `mode`,
    `ai-title`, and `file-history-snapshot`. Skip any `type` you don't recognize rather than
    trying to enumerate every one that exists.
- If the path is missing, unreadable, or doesn't parse as JSONL: say so in one line, then fall back
  to the live conversation. Never hard-fail.

## 2. Check what already exists

Before suggesting anything, `Glob` for:

- `.claude/skills/**/SKILL.md`, `.claude/commands/*.md`, `.claude/agents/*.md` (project-local)
- `~/.claude/skills/*/SKILL.md`, `~/.claude/commands/*.md`, `~/.claude/agents/*.md` (global)

Read only the `name` and `description` frontmatter of each. You're building a cheap map of what's
already covered, not auditing them. Missing or empty `.claude` trees just mean an empty inventory;
skip the check, don't error.

**The global side can be slow on a real machine.** A real `~/.claude` can be large enough that one
deep recursive glob over the whole tree is slow or hangs. That's why the global pattern above is
one level deep (`*/SKILL.md`), not `**`. If it's still slow, or errors, treat that side as empty
and move on. A slow inventory must degrade exactly like a missing one: it must never block the
run.

## 3. Find candidates (genesis only)

Suggest a new tool only when at least one of these holds, and nothing from step 2 already covers
it:

- **Repetition**: the same manual action or shape of action (same Bash command pattern, same
  multi-step sequence) shows up **twice or more** in the reviewed conversation.
- **One substantial reusable workflow**: a single manual sequence happened that's clearly going to
  come up again, even though it only happened once here.
- **Explicit ask**: the user said something like "I do this every time," "ugh, this again," or
  asked outright for something like it.

**Default to silence.** If nothing clears that bar, say so plainly:

> Nothing stood out as worth a new tool this time.

Never invent a candidate to have something to report. A weak, hedge-everything suggestion is worse
than no suggestion. It trains the user to stop reading the output.

For each real candidate, capture: a short kebab-case name idea, one line on what it would do, its
likely shape (`skill`, `command`, or `hook`), and the concrete evidence (quote the message, or
describe the repeated calls plainly, e.g. "ran `git log --oneline | grep feat:` by hand 3 times").

## 4. Present the list

Most-evidenced candidate first. Plain numbered list, one short paragraph each: name, what it does,
why (the evidence). No more ceremony than that. This is a quick read, not a report.

Close with a one-line prompt: which one(s) to build, or none.

## 5. Offer to build

For each candidate the user picks:

1. Check (best-effort, non-fatal either way) whether the Superpowers `brainstorming` skill looks
   available in this environment. If it does, mention it as an option: a fuller pass through
   clarifying questions and a written spec, versus a quick draft right now. Let the user choose.
2. **Quick draft path** (the default, and also what to do when Superpowers isn't available): write
   a minimal working first version of the file directly.
   - `skill` → `.claude/skills/<name>/SKILL.md` with real frontmatter (`name`, `description`,
     `when_to_use`) and a short numbered procedure grounded in the evidence you already gathered.
     Not a placeholder: an actual first attempt at the real steps.
   - `command` → `.claude/commands/<name>.md` with `description`, `allowed-tools`, and the steps.
   - **Show the full content before writing anything.** Ask for approval. Only write the file once
     the user says yes. Never install silently. This mirrors the one invariant the private system
     this was cut from also enforces for new-tool proposals.
3. After writing, say exactly what was created and where, and that it's a first draft worth trying
   against a real case before trusting it.

## What this skill never does

Never proposes a change to an existing skill, command, agent, or hook. Never reports on error
rates, trigger accuracy, or model/effort fit for tools already in use. That's a different kind of
review, out of scope here on purpose. Never keeps a log or ledger between runs; every invocation is
a fresh read of whatever conversation or transcript it's pointed at.
