# Contributing

The useful parts of these guides came from things going wrong. A failure report is worth more here
than a suggestion, because the failure is the part nobody can invent from a desk.

## Worth reporting

**A step that failed on your setup.** Which guide, which step, what you ran, what happened. Your
shell, OS and Claude Code version matter, since a lot of this touches paths and hooks.

**A router class that mis-tiers.** If `router_cli.py classify "..."` returns the wrong class for a
prompt you actually typed, that is a real bug and the prompt itself is the bug report. Paste it.
Same for a class that routes to a model that turned out to be too weak or needlessly expensive.

**A `doctor` check that lied.** A check reporting PASS when the thing was broken is worse than no
check. That has already happened once and the fix made the verdict INCONCLUSIVE instead.

**A hook that silently did nothing.** These fail quietly by design so they cannot block prompt
submission, which makes them easy to misdiagnose. If yours never fired, say what you configured.

## Less useful

Style changes to the prose, renamed variables, and reformatting. Not unwelcome, just low value
against the failure reports.

Requests to support a provider or model that nobody here can test. Happy to take a patch with the
reasoning written down; less happy to guess at behaviour and publish it as fact.

## If you send a patch

Keep the diff small enough to read in one sitting. Match the surrounding style rather than
introducing a new one.

For anything under `ModelRouter/`, run the self-test first and say that you did:

```
python .claude/hooks/router_cli.py doctor
```

New task classes need a pattern, a table entry with an unconditional fallback last, and a test case
in `_CASES` including one prompt that should **not** match. Order matters in `CLASS_PATTERNS`, so
say where you put yours and why.

## Scope

This is a personal toolkit published because the material was worth sharing, not a product with a
support commitment. Issues get read. Nothing is guaranteed to get fixed on a schedule.
