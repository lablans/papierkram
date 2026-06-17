---
name: verify-project
description: >
  Verify a project's SharePoint documents against its index.md: enumerate live files,
  run the completeness check, reconcile the SharePoint Documents table, and write back.
  Triggers: step 7 of add-project, "verify project", "check project", "audit project",
  "update a project".
---

# Verify a Project

The SharePoint Documents table in `index.md` is a cache of the live folder. This workflow
re-validates it against SharePoint and **reconciles** the table — it is the single source
of truth for the table's contents. It does **not** blindly overwrite: the `Document` label
column is human-curated (e.g. "Institutional Endorsement", "Verwertungsplan") and cannot be
re-derived from filenames, so labels are preserved.

## Required Documents reference (mirror of CLAUDE.md — apply in Step 3)

**Emit one line per missing document:**
> ⚠️ Missing required document: **<name>** — required because <reason>

| Document | Required when | Keywords / naming hints | Canonical filename |
|---|---|---|---|
| Budget table | always | "budget", "Kosten", "Finanzplan", "Kalkulation"; `.xlsx` extension | `Budget.xlsx` |
| Grants office checklist | DKFZ projects only (`institution: DKFZ`) | "checklist", "Checkliste" | `Checklist.docx`, `Checklist.pdf` |
| Part A — applicant info | EU projects (funder: EC, EU, ERC, or similar) | "Part_A", "PartA", "Teil_A", "administrative", "Info Collector", "InfoCollect"; contains PIC number of the institution | ~ |
| Part B — proposal text | always | "proposal", "Antrag", "Part_B", "PartB", "Teil_B", "full" | ~ |
| AZAP/AZK | BMBF proposal, once submitted (`submitted:` is a date) | "AZAP" (DKFZ), "AZK" (UMM) | `AZAP.pdf` |

**Document location by status:**

| Status | Expected SharePoint location |
|---|---|
| `proposal`, `rejected` | `sharepoint_folder` (root) |
| `ongoing`, `finished` | `<sharepoint_folder>Management/Anträge/` |

---

## Workflow

**Step 1 — Determine the documents base.**
From `status` (see table above):
- `proposal`, `rejected` → `sharepoint_folder` (root)
- `ongoing`, `finished` → `<sharepoint_folder>Management/Anträge/`

**Step 2 — Enumerate live files.**
List the base with `sp.py --list <base>`. `sp.py --list` is **non-recursive**; if the
listing contains subfolders, issue one additional `--list` per immediate subfolder to
enumerate their files (descend **one level** below the base). Do not recurse deeper — flag
any subfolder nested deeper than one level below the base as a **layout deviation** (note
it in the report but do not chase it).

Enumeration only sees files at or one level below the base. Existing table rows whose
`File` points *outside* the base (e.g. a stray directly under `Management/` for an
`ongoing` project) will therefore not appear in the enumeration; do not treat that as a
deletion — see Step 4. Such out-of-base rows are themselves layout deviations and should be
listed in the report.

**Step 3 — Completeness check.**
Run the Required Documents check above against the enumerated files and emit a missing-document
warning for each one not found.

**Step 4 — Reconcile the table.** For each live file, compute its `File` value (path
relative to `sharepoint_folder`, decoded/human-readable):
- **Match by filename** (the last path segment) to an existing table row. If matched, keep
  the row's `Document` label and refresh its `File` value to the live relative path.
- **Live file with no matching row** → append a new row with a best-effort `Document` label
  derived from the filename, marked `(review label)` so the user knows to confirm it.
- **Existing row whose file is no longer present live** → keep the row but mark it
  `⚠️ not found` rather than deleting it (the file may have been moved or renamed). Exception:
  if the row's `File` lies *outside* the documents base (so enumeration never covered it),
  trust it as-is — do not mark it not-found — and report it as a known layout deviation.

**Step 5 — Compliance report.** Summarize for the user:
- required documents present vs. missing,
- new files added to the table (with their provisional labels),
- rows marked not-found,
- layout deviations (files outside the expected base / nested too deep),
- any `_v1` / `_v2` / `_old` / `_final` duplicate filenames on SharePoint — flag these per
  the Versioning policy and remind the user to delete the duplicates.

**Step 6 — Write back.** Update the SharePoint Documents table in `index.md` with the
reconciled rows.
