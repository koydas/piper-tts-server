---
name: new-adr
description: Scaffold a new Architecture Decision Record in docs/adr/, following the existing numbering and section format, and update the index. Use when a real decision was made — not for routine changes.
---

# new-adr

## When to Apply

When making a design or technical decision worth remembering the reasoning for: how the
voice model is packaged/loaded, the API shape, deployment topology, or anything where a
future reader would otherwise have to re-derive "why is it built this way?" from scratch.
This is a small, mostly-settled repo — most changes here are routine and don't need one.

## Expected Behavior

### Step 1 — Determine the next ADR number

```bash
ls docs/adr/[0-9][0-9][0-9][0-9]-*.md | sort
```

Take the highest number and increment by one, four digits zero-padded. Only one ADR exists as
of this writing (`0001-bake-voice-model-at-build-time.md`) — always check the current count
rather than assuming a number.

### Step 2 — Create the ADR file

`docs/adr/<NNNN>-<kebab-case-title>.md`:

```markdown
# ADR-<NNNN>: <Title>

- **Date:** <YYYY-MM-DD>
- **Status:** Accepted

## Context

[What problem or situation prompted this decision?]

## Decision

[What was decided, and how does it work? Name the actual files involved.]

## Alternatives Considered

[What else was considered, and why was it rejected?]

## Consequences

[Trade-offs. Good/Neutral/Negative, with ⚠️ for drawbacks/caveats.]
```

Read `docs/adr/0001-bake-voice-model-at-build-time.md` first to match tone and level of
detail.

### Step 3 — Add to the index

Append a line to `docs/adr/README.md`'s `## Records` list. An un-indexed ADR is effectively
invisible — don't skip this.

### Step 4 — Cross-link from the source and docs

Check whether `docs/architecture.md` or `docs/deployment.md` need a matching update (a new
diagram, an updated explanation).

## Constraints

- ADR numbers must be sequential with no gaps.
- Status must be `Accepted` (or `Proposed` if genuinely still under discussion).
- Don't write an ADR for something reversible and inconsequential.
- Ask before pushing — a push here can also trigger a rebuild/deploy if it touches anything
  outside `docs/**`/`**.md` (an ADR-only change won't).

## References

- `docs/adr/README.md` — the index to update
- `docs/adr/0001-bake-voice-model-at-build-time.md` — length/tone reference
- `docs/architecture.md`, `docs/deployment.md` — diagrams/narrative that may need a matching
  update alongside a new ADR
