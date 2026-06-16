---
name: plan-feature
description: Write a tracked design plan to plans/YYYY-MM-DD-<slug>.md before implementation begins. Use when the user describes a new feature, non-trivial change, or refactor and wants to align on approach first. Pauses for human sign-off before any code is touched.
---

# /plan-feature

The user's workflow is: **define → plan → implement → test locally → push**. This skill is the plan step. It always produces a markdown file in `plans/` so the rationale lives next to the diff in git history.

## Process

1. **Take the feature description.** It may come in args or in the user's prior message. If the description is too thin to plan against, ask one or two targeted questions before writing — but don't over-interrogate. Most plans are better written and then refined than blocked on perfect inputs.

2. **Pick a slug.** Short kebab-case derived from the feature name. Two or three words. Today's date prefix is the calendar date in `YYYY-MM-DD`.

3. **Write `plans/<YYYY-MM-DD>-<slug>.md`** using the template below. Mark it `Status: draft`.

4. **Show the plan to the user and stop.** Do not start implementation. Wait for explicit approval (e.g. "looks good", "go ahead", or revisions). When approved, flip the status to `approved` in the same file before any code changes.

5. **When the feature ships,** flip the status to `shipped` in the same PR as the merge.

## Template

```markdown
# <Feature title>

Status: draft
Date: <YYYY-MM-DD>

## Objective
One or two sentences. What changes for the user, or what capability is added.

## Context
Why now. Any prior conversation, related plan, or bug that motivated this. Link to issues, PRs, or other plans if applicable.

## Approach
The shape of the solution in plain prose. Not pseudocode — the level of detail a senior reviewer would want before reading the diff. Mention key trade-offs and why this approach over alternatives.

## Files to touch
- `path/to/file.ext` — role of change (one line)
- ...

## API / data shape
Any new endpoints, request/response shapes, DB columns or migrations. Skip this section if there are none.

## Tests
- Backend (pytest): which test files, what cases.
- Frontend unit (vitest): which composables/stores/components.
- E2E (playwright): which user flow, if any.
Lean on TDD for pure logic (composables, Flask endpoints) where contracts are clear.

## Security considerations
This site is exposed on a home server. For each change, answer:
- Does this introduce a new input vector? How is it validated/escaped?
- Does this expose internal state (paths, secrets, IDs)?
- Does this weaken the network boundary (new port, new origin, relaxed CORS, weakened CSP)?
If the answer to all three is "no", say so explicitly.

## Out of scope
What this plan deliberately does **not** cover.

## Open questions
Anything blocking or worth a second opinion before approval.
```

## Notes

- Keep plans concise. Aim for half a page. If a plan grows past ~200 lines, the feature is probably too big for one plan and should be split.
- Don't repeat content already in `AGENTS.md` — link or reference instead.
- If the user pivots mid-implementation, update the existing plan rather than writing a new one. Add a short "Revision" section at the end with the date and what changed.
- If a plan is abandoned, leave the file in place, set status to `abandoned`, and add a one-line note at the bottom explaining why.
