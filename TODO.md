# TODO

## Metadata: funding expressed in person-months (PM) vs. Euros

**Problem.** The project frontmatter currently models funding only as `amount_requested`
(EUR, direct costs excl. overhead). But our DKFZ contribution is sometimes specified in
**person-months**, not Euros — and the two don't convert without a €/PM rate plus
non-personnel direct costs. Example: `2026_EC_GenAI4RI` lists DKFZ at **19 PM** (WP1/WP3/WP4)
with empty budget tables and no budget XLSX, so `amount_requested` had to be left `~`.

**Decide how to structure / request this metadata:**

- Add a dedicated effort field (e.g. `effort_pm:`) so a project can record PM when no EUR
  figure exists yet — instead of forcing everything into `amount_requested`.
- Decide whether to keep PM and EUR side by side, and whether to store a per-PM rate so one
  can be derived from the other.
- Update the "Adding a new project" workflow (CLAUDE.md) to ask for PM **or** EUR (or both),
  and to extract whichever the proposal actually provides.
- Define how `projects/README.md` shows the figure when only PM is known (today it shows `~`).

**Context:** raised 2026-06-15 while adding GenAI4RI.
