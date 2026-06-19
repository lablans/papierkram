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

## Filenames: original (partner) names vs. harmonized naming

**Tension.** Two goals pull in opposite directions for files stored on SharePoint:

- Keeping partners' **original filenames** is valuable — partners tend to keep their own
  names, so the original name is how we *recognize* an incoming file.
- We also need **harmonized, consistent naming ACROSS all applications** in our document
  management, so the same kind of document is findable the same way in every project.

The current CLAUDE.md "Naming on upload" policy leans toward canonical names
(`Budget.xlsx`, `Checklist.docx`, …), but real folders don't follow it: e.g.
`2026/LSRI-Amplify/` holds `Checklist_EN_LSRI-Amplify.docx`,
`LSRI-AMPLIFY (INFRA-DEV-02) Proposal Draft.docx`, `LSRI_Amplify_LS.xlsx` — all descriptive,
partner-exchange-style names.

**Decide:**

- A rule that captures both — e.g. canonical names only for the few **required / cross-project**
  documents (Budget, Checklist, Part A/B), while **preserving original names** for
  partner-exchanged drafts and supporting files.
- Whether to map original→canonical via the curated `Document` label instead of renaming the
  file at all (relates to the "Do we even need the table?" item above).
- Update CLAUDE.md "Naming on upload" accordingly so policy matches practice.

**Context:** raised 2026-06-19 while uploading LSRI Amplify's proposal PDF and budget XLSX
(kept their original names to match the folder's existing convention).

## Model "affiliated entity" participation type

**Problem.** DKFZ frequently joins EU consortia as an **affiliated entity** of another
beneficiary, not as a direct beneficiary. The frontmatter `role` field only models a
*personal* role (PI | Co-PI | Coordinator); it has no field for the **organizational
participation type** (Coordinator / Beneficiary / Affiliated Entity / Associated Partner) or
for the **lead beneficiary** we are affiliated through.

Example: in `2026_EC_LSRI-Amplify`, DKFZ is an **affiliated entity of BBMRI-ERIC** (Part A
participant #3, role "Affiliated", controlled-by link to participant #2). Recorded for now
as `role: PI` with the affiliation only in a frontmatter comment + Notes.

**Decide:**

- Add a `participation:` field (`beneficiary` | `affiliated_entity` | `associated_partner` |
  `coordinator`) and an `affiliated_via:` / `lead_beneficiary:` field.
- Update the add-project workflow (CLAUDE.md) to extract participation type from the Part A
  participant list, and decide how `projects/README.md` should surface it.

**Context:** raised 2026-06-19 while adding LSRI Amplify; the user noted this case recurs often.

## Define `amount_requested` precisely

**Problem.** The field is labeled "direct costs requested in EUR (excl. overhead)", but in
practice it is filled on inconsistent bases:

- For **actual-cost** grants the "excl. overhead" net figure is well-defined.
- For **lump-sum** grants (e.g. `2026_EC_LSRI-Amplify`) there is no separable overhead line at
  award level, so the value recorded is the **gross** requested lump sum (indirect embedded).
- It is also unclear whether the figure should be **DKFZ's share** or the **whole consortium**
  (current practice: DKFZ's share — but undocumented and unverified across projects).

This makes cross-project comparison (and the `projects/README.md` Amount column) unreliable.

**Decide:**

- A precise, grant-type-aware definition: gross vs. net of overhead, DKFZ-share vs. total,
  and what to record when only a lump sum / only person-months exist (see the PM-vs-EUR item).
- Whether to store the basis alongside the number (e.g. `amount_basis: lump_sum_gross |
  direct_excl_overhead`) so figures are comparable, and update CLAUDE.md / add-project to set it.

**Context:** raised 2026-06-19 while adding LSRI Amplify, whose €57,625 (DKFZ gross lump sum)
is not on the same basis as e.g. COHESION's €481,455.
