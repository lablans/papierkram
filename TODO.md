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

## Do we even need the SharePoint Documents table?

**Question.** Each `index.md` carries a SharePoint Documents table (now `Document | Type |
File`, with `File` a path relative to `sharepoint_folder`). Could we drop the stored table
entirely and discover the documents **live** from SharePoint instead?

**Decide:**

- Whether the table earns its keep, or whether listing the folder on demand (`sp.py --list`)
  would be enough — given live listing needs `rbw` unlocked + auth, whereas the table is
  readable offline and feeds cross-project questions that deliberately avoid SharePoint.
- If we keep a stored table, whether the curated `Document` label column is the only part
  worth storing (filenames + types are derivable from a listing; labels are not).
- If we go live, where the human labels would come from (a small name→label map? canonical
  filenames only? drop labels?), and how cross-project / offline queries cope without them.
- Interaction with the "Verifying a project" reconcile workflow — if discovery is live, the
  reconcile step largely disappears.

**Context:** raised 2026-06-15 after switching the table from full URLs to relative paths;
the relative-path change reduced but did not remove the de-sync concern.
