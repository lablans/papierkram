---
name: add-project
description: >
  Add or update a grant/project in the papierkram repo. Collects inputs, discovers
  SharePoint documents, extracts proposal text, generates or updates index.md and
  README row, then runs verify-project. Triggers: "add a grant", "new proposal",
  "new project", "update project info", "update a project".
---

# Add / Update a Project

## Required Documents reference (mirror of CLAUDE.md — apply in Step 2 and Step 7)

**Emit one line per missing document:**
> ⚠️ Missing required document: **<name>** — required because <reason>

| Document | Required when | Keywords / naming hints | Canonical filename |
|---|---|---|---|
| Budget table | always | "budget", "Kosten", "Finanzplan", "Kalkulation"; `.xlsx` extension | `Budget.xlsx` |
| Grants office checklist | DKFZ projects only (`institution: DKFZ`) | "checklist", "Checkliste" | `Checklist.docx`, `Checklist.pdf` |
| Part A — applicant info | EU projects (funder: EC, EU, ERC, or similar) | "Part_A", "PartA", "Teil_A", "administrative", "Info Collector", "InfoCollect"; contains PIC number of the institution | ~ |
| Part B — proposal text | always | "proposal", "Antrag", "Part_B", "PartB", "Teil_B", "full" | ~ |
| AZAP/AZK | BMBF proposal, once submitted (`submitted:` is a date) | "AZAP" (DKFZ), "AZK" (UMM) | `AZAP.pdf` |

**Naming on upload:** use canonical filename above; where `~`, strip language markers (`_EN`, `_DE`) and version suffixes (`_3`, `_v2`, `_final`, `_draft`). Rely on SharePoint versioning, not the name.

**Document location by status:**

| Status | Expected SharePoint location |
|---|---|
| `proposal`, `rejected` | `sharepoint_folder` (root) |
| `ongoing`, `finished` | `<sharepoint_folder>Management/Anträge/` |

## Upload safeguards (apply before any upload in Step 5 or Step 7)

- **Dry-run first, always.** Run `sp.py --upload <file> <dest>` without `--confirm`. Show the dry-run output to the user before doing anything.
- **Explicit per-file authorization required.** Only add `--confirm` when the user has explicitly asked to upload *that file* to *that destination*. Showing the dry run does not authorize the write.
- **One approval is never standing approval** — confirm again for each new upload.
- **Updating an existing file** requires `--confirm --update`. Before running, compare content (not just sha256) — see "Compare before updating" in CLAUDE.md.

---

## Workflow

**Step 1 — Collect required inputs from the user.**
Ask for all fields that cannot be inferred from the proposal document. Ask them together in a single message, not one at a time:

- `sharepoint_folder` — URL to the SharePoint directory containing the proposal files
- `institution` — DKFZ or UMM
- `role` — PI, Co-PI, or Coordinator
- `deadline` — submission deadline (from the call announcement, ~ if not applicable)
- `status` — default `proposal` unless told otherwise

**Step 2 — Discover documents.**
If the user provides an `AllItems.aspx?id=...` SharePoint URL, convert it to a direct path URL first: URL-decode the `id` parameter value and use that as the path (append a trailing `/`). For example, `?id=%2Fsites%2Fverbis%2Fpantr%2F2026%2FCOHESION` → `https://webcoop.inet.dkfz-heidelberg.de/sites/verbis/pantr/2026/COHESION/`.

List the SharePoint folder using `sp.py --list <sharepoint_folder>`. Identify the main proposal file (largest PDF or DOCX, or one named "proposal"/"Antrag") and the budget file (XLSX or a clearly named PDF).

**Run document completeness check now** — apply the Required Documents rules above to the listing. Emit a warning for every required document not found in the listing before proceeding. Do not skip this even if the document table looks complete at a glance.

**Step 3 — Extract proposal text.**
Download the main proposal document to `tmp/` via `sp.py`. Extract its text using existing skills to read pdf and microsoft office files.

**Step 4 — Generate frontmatter and summary.**
From the extracted text, derive:
- `title`, `funder`, `program`, `acronym`, `amount_requested`, `period` — from cover page or header
- Summary paragraph — from the abstract or Zusammenfassung section
- Document table rows — one row per file found in step 2

For `amount_requested`: use **direct costs only, excluding overhead/indirect costs**. If the proposal document contains placeholder values (`XXX €`), fall back to the budget XLSX. In the budget XLSX the overhead line is typically labelled "Indirect Costs" or shown as a flat-rate percentage row — subtract it from the total eligible costs to get the direct cost figure.

**Step 5 — Create or update files.**
Determine the folder name as `YYYY_FUNDER_ACRONYM` using the deadline year (or current year if no deadline).

```
projects/YYYY_FUNDER_ACRONYM/index.md
```

Write `index.md` with the full frontmatter and body. Then add or update one row in `projects/README.md`
(create the file with a header row if it does not yet exist):

```markdown
| Acronym | Funder | Institution | Status | Deadline | Amount | Folder |
```

**Step 6 — Confirm.**
Show the user the generated `index.md` and ask them to verify the auto-extracted fields
(title, funder, amount, period) before finishing.

**Step 7 — Verify layout (run after user confirms).**
Run the full `verify-project` skill on the newly created or updated project and show the compliance report to the user alongside the confirmation. This ensures the repo and SharePoint are consistent from the start.
