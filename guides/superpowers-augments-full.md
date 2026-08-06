# Superpowers Brainstorming: Full Augment Set

[Superpowers](https://github.com/obra/superpowers) ships a `brainstorming` skill that walks you from
a vague idea to a written implementation plan. It is good. Out of the box it is also chatty, because
it stops for approval at the end of every phase.

This is the full set of augments used to change that behaviour, written as a drop-in preferences
file. User instructions override skill instructions in Claude Code, so none of this requires editing
the plugin. That matters, because plugin updates overwrite the plugin's own `SKILL.md` and take your
edits with them.

If you only want the part that assigns models to implementation subagents, use
[superpowers-augments-router-only.md](./superpowers-augments-router-only.md) instead. It is a strict
subset of this file.

---

## Install

**1. Save the preferences file.** Copy the block below to `~/.claude/superpowers-prefs.md`.

**2. Import it from your global instructions.** Add one line to `~/.claude/CLAUDE.md`:

```markdown
@superpowers-prefs.md
```

The `@` import is resolved relative to the file doing the importing, so a bare filename works when
both live in `~/.claude/`.

**3. Confirm it loaded.** Start a session and run `/context`. The imported file should appear under
your user instructions. If it does not, the usual cause is that `~/.claude/CLAUDE.md` does not exist
at all, in which case create it.

For a single project instead of the whole machine, put the same content in
`<project>/.claude/CLAUDE.md` or import it from the project's root `CLAUDE.md`. Project instructions
load on top of global ones.

---

## What each augment changes, and why

Read this part before installing. Some of these trade safety for speed, and you should know which.

### Run every phase, stop only twice

The default skill treats each phase boundary as an approval gate. The augment keeps all the phases,
because the reasoning in each one is real and ends up in the written plan, but removes the gates.

Two stops remain. The clarifying-questions phase, because that is where your intent enters the
system and guessing is expensive. And the single confirmation before implementation, because that is
the last point where the work is still cheap to redirect.

The cost: if the design phase goes somewhere you would have vetoed, you find out at the
pre-implementation stop rather than immediately. In practice the design phase is shown in full
before the plan is written, so you can still interrupt.

### Question formatting

Numbered options, never Greek letters. A `Q n/total` counter so you know how long the questioning
runs. The recommended option first, marked at the option's title level rather than buried in the
description subtext. One-key accept.

The title-level marking is the part that actually matters. A recommendation in small grey text under
a heading gets skipped, and then you are grading options the assistant already had an opinion about.

### Approaches, design and plan run without gates

The skill still generates candidate approaches and reasons through them, because that thinking
improves the result. It just does not make you grade them. It recommends one and offers to proceed.

Same for design and plan. Perform the phase, show it once, treat it as approved.

### The one real stop, before implementation

Default to subagent-driven execution, one fresh subagent per task. Do not offer "subagents versus
inline" as a choice, because inline execution on a planning-tier session is the expensive mistake
this whole file exists to prevent.

At that stop, three things get offered:

- An isolated worktree, if the project has a command for it.
- A swap to a fresh session, along with a self-contained copy-paste implementation prompt in a code
  block, so the plan survives the context switch.
- The model map for the plan's tasks, so you see the cost shape before you approve it.

### Subagent model and effort policy

This is the load-bearing augment. It is described in full in the router-only guide, and reproduced
in the file below.

The short version: **never dispatch a subagent without an explicit `model` parameter.** An omitted
model inherits the session model, and on a top-tier planning session that multiplies your most
expensive model across every task in the plan.

### Verification gates go through a test runner, not raw shell

Baseline and completion gates that run `tsc`, `eslint`, `pytest`, `cargo`, `vitest` or a build get
dispatched to a dedicated `test-runner` agent rather than invoked as ad-hoc shell with hand-parsed
output.

This one came from a repeat finding, five recurrences before it was written down. Raw shell gate
runs scatter test invocations across the transcript, drop the pass/fail classification the test
runner enforces, and burn main-context tokens on output nobody reads. Direct shell stays available
for one-off diagnostics.

---

## The file

Save as `~/.claude/superpowers-prefs.md`.

```markdown
# Superpowers Brainstorming: workflow preferences

> User instructions override plugin defaults, so these apply wherever the plugin runs. Do not edit
> the plugin's own SKILL.md, since plugin updates overwrite it.

**Go through every phase, but do not stop at each one.** Run all the natural brainstorming phases
(clarifying questions, approaches, design, plan) and actually produce each artifact. Do NOT pause
for approval at each phase: show the conclusion briefly, treat it as auto-approved, and continue.
The ONLY stops are (1) the clarifying-questions phase and (2) the single confirmation before
implementation.

- **Questions:** number options `1/2/3` (never Greek letters; capitals are fine for three or fewer
  choices). Show a `Q n/total` counter on the question line. List the **recommended option first and
  mark it prominently at the option's title level** (e.g. `* Recommended`). Never bury the
  recommendation in the small description subtext. Offer one-key accept ("press 1 to take the
  recommendation"). If the user says "use recommended" or "auto" or "recommended for all", take the
  recommended choice at every remaining gate through to a finished plan, without stopping.
- **Approaches:** generate and reason through the candidate approaches, then recommend the best one
  and offer a quick "proceed with recommended." Do not make the user grade them unless they ask.
- **Design phase:** perform it (architecture, components, data flow, error handling, testing) and
  show it in one message, but treat it as **auto-approved**. No per-section acknowledgement gates.
- **Plan:** write the plan once the approach is set. Never ask "shall I write the plan?".
- **Before implementation (the one real stop):** default to **subagent-driven** execution, one fresh
  subagent per task, each with an **explicit `model` parameter** per the policy below. Do NOT offer
  "subagents vs inline" as a choice. Announce subagent-driven and wait for the user's go. If the
  project provides an isolated-worktree command, offer it first. Also offer to swap to a fresh
  session and wrap up this one, and at that same point ALWAYS emit a self-contained copy-paste
  implementation prompt in a code block, so the plan can be pasted into the fresh session.

## Subagent model and effort policy (ALL subagent-dispatching skills)

Applies to `subagent-driven-development`, `executing-plans`, `dispatching-parallel-agents`, and any
other flow that spawns task subagents. Rationale: planning is expensive on purpose. Brainstorm,
design and plan phases run inline at the session model, which the user deliberately sets to the
highest tier. That model must NOT leak into the implementation fleet.

- **Never dispatch a subagent without an explicit `model` parameter.** An omitted model inherits the
  session model. On a top-tier planning session that multiplies the most expensive model across
  every task. Treat a model-less dispatch as a bug.
- **Default model assignments** (deviate per task only with a stated reason):

  | Role | Model |
  |------|-------|
  | Mechanical implementation task (1-2 files, complete spec) | `haiku` |
  | Standard implementation or multi-file integration (default when unsure) | `sonnet` |
  | Spec-compliance reviewer | `sonnet` |
  | Code-quality reviewer | `sonnet` (`opus` only for security/auth, data migration, or concurrency-critical tasks) |
  | Re-dispatch after BLOCKED, or an architectural judgment call | `opus` |
  | Baseline or completion **verify gate** (tsc, eslint, pytest, cargo, vitest, build) | `haiku` for a single-framework suite; `sonnet` for a multi-crate or multi-framework gate, where a small model at low effort mis-parses failures |
  | **Final whole-implementation verification** (the last step of the plan) | **the session's top model** |

  Planning AND final verification both run at the highest tier. Only the middle drops down.

- **Route verify-gate runs through the `test-runner` agent, not raw shell.** In
  `subagent-driven-development` and `executing-plans`, the baseline gate before a task and the
  completion gate after it MUST be dispatched to the `test-runner` agent rather than invoked as
  ad-hoc shell with hand-parsed output. Raw shell gate runs scatter test invocations, drop the
  pass/fail classification the agent enforces, and burn main-context tokens on output. Reserve
  direct shell for one-off diagnostics. `test-runner` defaults to `haiku` at low effort. When the
  gate spans multiple frameworks, dispatch it with `model: sonnet`.

- **Per-agent effort:** agent frontmatter supports `effort:` (low, medium, high, xhigh, max, model
  dependent). Ad-hoc subagent dispatches inherit session effort, since there is no per-call effort
  parameter. At the pre-implementation stop, remind the user to lower session effort before a large
  inherited-effort fleet dispatch.

- **Announce the cost shape before "go":** one line stating the model map for the plan's tasks
  (e.g. "7 tasks: 5x sonnet + 2x haiku, reviews sonnet, final review opus") so the user sees the
  token profile before approving.

**Choice presentation (ALL skills and commands, not just brainstorming):** every multi-option prompt
marks the recommended choice first and prominently, and accepts a one-key shortcut. "Use recommended
for all" auto-accepts recommendations for the remainder of the flow.
```

---

## Optional: a deep-thinking gate

If you have access to more than one top-tier model, or a model whose availability changes (a trial,
a weekly cap, a credit balance), add a gate that decides once at the start of the flow rather than
interrupting mid-plan.

The pattern that works: check availability during phase one, fold the choice into the
clarifying-questions stop as a single extra question, and never raise it again mid-flow. Always arm
a fallback, so a failed dispatch on the preferred model retries on the standard one instead of
stalling.

The anti-pattern is checking availability at dispatch time. That puts a question in front of the
user at the exact moment the plan was about to execute, which is the worst possible moment for it.

---

## Notes and caveats

**These are preferences, not guarantees.** Claude Code applies user instructions with priority over
skill instructions, but a long session can drift. If you notice phase gates coming back, the
preferences file has probably fallen out of context. `/context` will tell you.

**The auto-approve behaviour is a real trade-off.** You get a finished plan in one pass instead of
five round trips. You also lose four natural interrupt points. If you are working in an unfamiliar
domain where you would want to correct the approach early, keep the default gated behaviour and use
only the subagent model policy section.

**The model names are examples.** `haiku`, `sonnet` and `opus` are tier labels. Substitute whatever
your setup actually has, and revisit the table when a new model lands, because the tier boundaries
move.
