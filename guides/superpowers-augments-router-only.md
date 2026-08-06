# Superpowers: Subagent Model Routing Only

This is the minimal augment for [Superpowers](https://github.com/obra/superpowers). It changes one
thing: which model each implementation subagent runs on when brainstorming hands off to execution.

It does not touch the brainstorming flow, the phase gates, or the question formatting. If you want
those too, use [superpowers-augments-full.md](./superpowers-augments-full.md), which contains this
file as a subset.

---

## The problem

Superpowers ends brainstorming by writing a plan, then hands that plan to
`subagent-driven-development` or `executing-plans`, which spawn one subagent per task.

Those subagents inherit the session model when no model is specified. You set the session model for
the hardest thing in the session, which is the planning you just finished. So a seven-task plan
dispatches seven subagents on your most expensive model, to do work that is mostly writing files
against a spec that is already complete.

Planning is expensive because judgment is expensive. Implementing a finished spec is typing. Paying
judgment prices for typing is the entire problem.

---

## Install

Save the block below to `~/.claude/superpowers-prefs.md`, then add this line to
`~/.claude/CLAUDE.md`:

```markdown
@superpowers-prefs.md
```

For one project rather than the whole machine, put the same content in the project's
`.claude/CLAUDE.md`, or import it from the project's root `CLAUDE.md`.

Verify with `/context` in a new session. The file should show up under user instructions.

---

## The file

```markdown
## Subagent model and effort policy (ALL subagent-dispatching skills)

Applies to `subagent-driven-development`, `executing-plans`, `dispatching-parallel-agents`, and any
other flow that spawns task subagents. Rationale: planning is expensive on purpose. The brainstorm,
design and plan phases run inline at the session model, which the user deliberately sets to the
highest tier. That model must NOT leak into the implementation fleet.

- **Never dispatch a subagent without an explicit `model` parameter.** An omitted model inherits the
  session model. On a top-tier planning session that multiplies the most expensive model across
  every task. Treat a model-less dispatch as a bug.

- **Default model assignments** (deviate per task only with a stated reason):

  | Role | Model | Effort |
  |------|-------|--------|
  | Mechanical implementation task (1-2 files, complete spec) | `haiku` | low |
  | Standard implementation or multi-file integration (default when unsure) | `sonnet` | high |
  | Spec-compliance reviewer | `sonnet` | high |
  | Code-quality reviewer | `sonnet` | high |
  | Code-quality reviewer for security, auth, data migration or concurrency | `opus` | xhigh |
  | Re-dispatch after a BLOCKED task, or an architectural judgment call | `opus` | xhigh |
  | Verify gate, single framework (tsc, eslint, pytest, cargo, vitest, build) | `haiku` | low |
  | Verify gate, multiple crates or frameworks | `sonnet` | medium |
  | **Final whole-implementation verification** (last step of the plan) | **session top model** | xhigh |

  Planning AND final verification run at the highest tier. Only the middle drops down.

- **Route verify-gate runs through the `test-runner` agent, not raw shell.** The baseline gate
  before a task and the completion gate after it MUST be dispatched to `test-runner` rather than
  invoked as ad-hoc shell with hand-parsed output. Raw shell gate runs scatter test invocations,
  drop the pass/fail classification the agent enforces, and burn main-context tokens on output.
  Reserve direct shell for one-off diagnostics.

- **Announce the cost shape before "go":** one line stating the model map for the plan's tasks
  (e.g. "7 tasks: 5x sonnet + 2x haiku, reviews sonnet, final review opus") so the user sees the
  token profile before approving.

- **Per-agent effort:** agent frontmatter supports `effort:` (low, medium, high, xhigh, max, model
  dependent). Ad-hoc subagent dispatches inherit session effort, since there is no per-call effort
  parameter. Before a large fleet dispatch, remind the user to lower session effort so the fleet
  does not inherit a high setting across every task.
```

---

## Why the table is shaped this way

**Both ends stay expensive.** The top tier appears twice, at architecture and at final verification.
Those are the two places where a cheaper model produces work that looks correct and is not, and
where the error propagates into everything downstream. The middle of a plan is well-specified by
construction, because the plan specified it.

**Verify gates are cheap but not free.** A gate run is mostly "run this command, read the output,
decide pass or fail." A small model at low effort handles that for a single framework. It stops
handling it when the output interleaves several frameworks, because then deciding what failed
requires actually parsing structure. That is the only reason the second gate row exists.

**Reviewers sit at mid tier except where being wrong is expensive.** Security, auth, data migration
and concurrency are the categories where a missed defect is not a bug report, it is an incident.

**Effort is a separate axis from model.** A cheap model at high effort and an expensive model at low
effort are different trades, and the table specifies both because specifying only the model leaves
half the cost undetermined.

---

## Checking it worked

Dispatch a plan and watch the first subagent's dispatch line. It should name a model. If it does
not, the preferences file is not in context, and the fleet is running on your session model.

The cost-shape announcement is the cheaper check, since it happens before anything is spent. If you
approve a plan and never saw a line like "7 tasks: 5x sonnet + 2x haiku," the policy did not load.
