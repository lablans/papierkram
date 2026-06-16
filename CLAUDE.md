# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

This repo ("papierkram" — German for paperwork) is a Claude Code workspace for document tasks: reading, summarizing, and managing files that live on DKFZ SharePoint servers.

## SharePoint skill

The `dkfz-sharepoint` skill (`sp.py`) authenticates to DKFZ on-premise SharePoint via ADFS and supports listing directories, downloading files, and — behind safeguards — uploading files.

### Prerequisites

- `rbw` (Bitwarden CLI) must be unlocked before calling `sp.py`; if it fails with "pinentry error: Inappropriate ioctl for device", ask the user to run `! rbw unlock` in their terminal. Credentials are fetched from the UUID in `.env`
- `.env` file (gitignored) must exist — copy from `.env.example` and fill in `DKFZ_SP_RBW_UUID`
- Python packages: `requests`, `python-dotenv`, `beautifulsoup4`

### Usage

```bash
# List a folder
python3 .claude/skills/dkfz-sharepoint/sp.py --list "https://webcoop.inet.dkfz-heidelberg.de/sites/verbis/pantr/"

# Download a file
python3 .claude/skills/dkfz-sharepoint/sp.py \
  "https://webcoop.inet.dkfz-heidelberg.de/sites/verbis/pantr/somefile.docx" \
  -o tmp/somefile.docx
```

A URL ending in `/` triggers listing automatically.

### Uploading files (guarded write path)

Uploading is the only operation that writes to SharePoint. It is deliberately gated. The command is:

```bash
# Dry run (default): reports source, size, sha256, destination, whether the
# target exists, and create-vs-update. Sends NOTHING.
python3 .claude/skills/dkfz-sharepoint/sp.py \
  --upload tmp/PartA.pdf \
  "https://webcoop.inet.dkfz-heidelberg.de/sites/verbis/pantr/2026/BBMRI-IMPACT/Part A.pdf"

# Actually transmit (creates a new file):
#   ... --confirm
# Update an EXISTING file (adds a new SharePoint version):
#   ... --confirm --update
```

Safeguards (do not work around them):

- **Dry-run is the default.** Nothing is transmitted without `--confirm`. Always run the dry run first and show its output to the user.
- **Create-only by default.** Uploading onto an existing file requires `--update` (which adds a new SharePoint version — never a `_v2` duplicate; see Versioning).
- **Write-path allowlist.** Uploads are refused unless the destination is under an allowed prefix (default `…/sites/verbis/pantr/`; override via `DKFZ_SP_WRITE_ALLOW_PREFIXES`).
- **Audit log.** Every actual upload attempt is appended to `.claude/skills/dkfz-sharepoint/uploads.log` (gitignored).

**Policy — never write without explicit, specific authorization:**

- Only run `--confirm` when the user has explicitly asked to upload *that file* to *that destination*. Showing the dry run does not by itself authorize the write.
- One approval is never standing approval — confirm again for each new upload.
- The `--confirm` invocation always triggers an approval prompt via a deterministic PreToolUse hook (`.claude/hooks/sp_upload_guard.py`), whose message names the destination and whether the write creates or updates a file. Do not attempt to bypass or suppress it.

### Compare before updating an existing file

When a dry run reports `action: update` (the destination already exists), **do not upload before confirming the content actually differs.** A re-saved file (e.g. a `.docx`/`.xlsx` opened and saved again) gets a different byte hash and may even keep the same size while its content is unchanged — uploading it would add a pointless SharePoint version.

Procedure:

1. Download the existing remote file to `tmp/` (e.g. `tmp/<name>_remote.docx`).
2. Compare against the local source. A differing `sha256` is **not** sufficient to conclude the content changed for zip-based Office formats. Compare *content*:
   - Office formats (`.docx`, `.xlsx`, `.pptx`) are ZIP archives — unzip both and `diff -rq` the unpacked trees. If every internal part is identical, the content is unchanged regardless of the outer hash.
   - For a quick text check, also `pandoc … -o` both and `diff` the output, but treat the unpacked-tree comparison as authoritative.
3. If the content is identical → **do not upload**; tell the user the remote copy already matches.
4. If the content differs → proceed with the normal guarded `--confirm --update` path (still requires explicit per-file authorization).

This applies only to updates. A `create` (target does not exist) needs no comparison.

### Known site prefixes

| Server | Base URL |
|--------|----------|
| webcoop | `https://webcoop.inet.dkfz-heidelberg.de/sites/verbis/` |
| intracoop | `https://intracoop.dkfz-heidelberg.de/` |

### Versioning

SharePoint's built-in versioning is the only versioning mechanism — files keep their canonical filename on SharePoint. Never upload or instruct the user to save `_v1`, `_v2`, `_old`, etc. suffixed copies to SharePoint. If the user does this, tell them off and remind them to delete the duplicates. Locally (e.g. `tmp/`), use `_v1`/`_v2` suffixes matching the SharePoint version label when downloading multiple versions for comparison.

### Reading or working with downloaded files

**Always** use the `document-skills` plugin for working with DOCX, XLSX, PPTX, and PDF files:

- XLSX / CSV → `Skill("xlsx")`
- DOCX → `Skill("docx")`
- PDF → `Skill("pdf")`
- PPTX → `Skill("pptx")`

If the plugin is not installed, tell the user to install it:

```
/plugin marketplace add anthropics/skills
/plugin install document-skills@anthropic-agent-skills
```

### Tracked changes and comments

These documents are living drafts exchanged between partners. Tracked changes
and comments are an ongoing debate about the text — whenever you read a document,
take that debate into account rather than treating it as a single resolved
reading.

- Extract with `pandoc --track-changes=all` and read `word/comments.xml`.
  (Pandoc's default silently accepts all changes, which hides the debate.)
- Distinguish settled text from text under revision: note the relevant pending
  insertions/deletions and comments, who made them, and how they bear on the
  matter at hand.
- When comparing two versions, compare with `--track-changes=all` — two files
  that are identical once accepted can still differ in what is under discussion.

### Python package dependencies

The document-skills plugin (and sp.py) require Python packages. If a package is missing, **do not find workarounds**: Just ask the user to install the package. Don't install it yourself.

## Project Repository Layout

```
projects/
├── README.md                        # master index table of all projects
└── YYYY_FUNDER_ACRONYM/
    └── index.md
```

Folder naming: `YYYY_FUNDER_ACRONYM` (e.g. `2025_DFG_PANTR`). The folder never moves when status changes — status lives only in the frontmatter.

### `index.md` frontmatter convention

```yaml
---
# Full official title of the project
title: "Full Official Grant Title"

# Funding agency (e.g. DFG, EC, BMBF)
funder: DFG

# Call / programme name
program: SPP 2306

# Short project name / acronym
acronym: PANTR

# Submitting institution (DKFZ | UMM)
institution: DKFZ

# Your role on the project (PI | Co-PI | Coordinator)
role: PI

# Lifecycle status (proposal | rejected | ongoing | finished)
status: proposal

# Date the proposal was submitted (ISO date or ~ if not yet)
submitted: ~

# Proposal submission deadline (~ if not applicable)
deadline: 2025-11-30

# Funding decision date (~ if not yet known)
decision: ~

# Direct costs requested in EUR (excl. overhead)
amount_requested: 450000

# Project duration: calendar span and runtime in months
period: 2025–2027
runtime_months: 24

# Keywords
tags: [pancreatic-cancer, single-cell]

# SharePoint folder URL for project documents
sharepoint_folder: https://webcoop.inet.dkfz-heidelberg.de/sites/verbis/pantr/
---
```

Fields `title`, `funder`, `program`, `amount_requested`, `period`, `runtime_months`, and the summary
paragraph are auto-generated from the proposal documents. The following must be
provided manually (not derivable from documents):

- `institution` — DKFZ or UMM
- `sharepoint_folder` — URL to the SharePoint directory
- `role` — your role on the project
- `deadline` — from the call announcement
- `status`, `decision` — updated over the project lifecycle

### `index.md` body convention

```markdown
# ACRONYM — Full Title

One-paragraph lay summary (auto-generated from abstract).

## SharePoint Documents

| Document | Type | File |
|---|---|---|
| Full Proposal | PDF | Part B.pdf |
| Budget Table | XLSX | Budget.xlsx |

## Key Contacts

## Notes
```

**Do not store full document URLs.** The `File` column holds each document's path
*relative to* `sharepoint_folder` — the host/site prefix is redundant with
`sharepoint_folder` and is the part most prone to de-sync. In the normal flat case
this is just the (canonical) filename, e.g. `Budget.xlsx`; for nested legacy layouts
it is a subpath, e.g. `Management/Anträge/2022_AZA/AZAP.pdf`.

Store the `File` value **decoded and human-readable** — literal spaces and umlauts,
never `%20` or other percent-escapes. (Filenames containing a literal `%`, `#`, or `?`
are not supported by this reconstruction scheme — they would be misread as escape/fragment/
query characters; none of the current documents have them.)

**Reconstructing the URL on demand:** concatenate `sharepoint_folder` (which always
ends in `/`) with the `File` value and pass the result straight to `sp.py`. `requests`
percent-encodes spaces and non-ASCII characters automatically, so no manual encoding is
needed:

```bash
# sharepoint_folder + File → live URL
python3 .claude/skills/dkfz-sharepoint/sp.py \
  "https://webcoop.inet.dkfz-heidelberg.de/sites/verbis/pantr/2026/COHESION/Budget.xlsx" \
  -o tmp/Budget.xlsx
```

The table is a cache of the live folder. Treat it as a snapshot to be re-validated, not
as ground truth — the "Verifying a project" workflow reconciles it against the live
listing.

## Required Documents

Every project must have specific documents on SharePoint. **Whenever you read or create a project `index.md`, run the completeness check below and emit a warning for every missing required document** — do not wait for the user to ask.

### Document requirements and naming

| Document | Required when | Keywords / naming hints | Canonical filename |
|---|---|---|---|
| Budget table | always | "budget", "Kosten", "Finanzplan", "Kalkulation"; `.xlsx` extension | `Budget.xlsx` |
| Grants office checklist | always | "checklist", "Checkliste" | `Checklist.docx`, `Checklist.pdf` |
| Part A — applicant info | EU projects (funder: EC, EU, ERC, or similar) | "Part_A", "PartA", "Teil_A", "administrative" | ~ |
| Part B - proposal text  | always | "proposal", "Antrag", "Part_B", "PartB", "Teil_B", "full" | ~ |
| AZAP/AZK | Only for BMFTR proposal, once submitted (`submitted:` field is a date, not `~`) | "AZAP" (DKFZ), "AZK" (UMM) | `AZAP.pdf` |

**Naming on upload:** give a required document its canonical filename from the column above. Where the canonical filename is `~`, derive a clean name yourself — strip language markers (`_EN`, `_DE`) and version/iteration suffixes (`_3`, `_v2`, `_final`, `_draft`) from the source filename. Rely on SharePoint versioning, not the name (see Versioning).

### Document location by status

| Status | Expected SharePoint location |
|---|---|
| `proposal`, `rejected` | `sharepoint_folder` (root) |
| `ongoing`, `finished` | `<sharepoint_folder>Management/Anträge/` |

For `ongoing` and `finished` projects, the documents should physically live in the `Management/Anträge/` subfolder. When checking or listing documents, use that subfolder URL.

### Warning format

Emit one line per missing document, prominently placed:

> ⚠️ Missing required document: **<document name>** — required because <reason (e.g. "all projects" / "EU funder" / "project is submitted")>

## Workflows

### Adding a new project

Trigger: user says "add a grant", "new proposal", "new project", or similar.

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

**Run document completeness check now** — apply the Required Documents rules to the listing. Emit a warning for every required document not found in the listing before proceeding. Do not skip this even if the document table looks complete at a glance.

**Step 3 — Extract proposal text.**
Download the main proposal document to `tmp/` via `sp.py`. Extract its text using existing skills to read pdf and microsoft office files.

**Step 4 — Generate frontmatter and summary.**
From the extracted text, derive:
- `title`, `funder`, `program`, `acronym`, `amount_requested`, `period` — from cover page or header
- Summary paragraph — from the abstract or Zusammenfassung section
- Document table rows — one row per file found in step 2

For `amount_requested`: use **direct costs only, excluding overhead/indirect costs**. If the proposal document contains placeholder values (`XXX €`), fall back to the budget XLSX. In the budget XLSX the overhead line is typically labelled "Indirect Costs" or shown as a flat-rate percentage row — subtract it from the total eligible costs to get the direct cost figure.

**Step 5 — Create files.**
Determine the folder name as `YYYY_FUNDER_ACRONYM` using the deadline year (or current year if no deadline).

```
projects/YYYY_FUNDER_ACRONYM/index.md
```

Write `index.md` with the full frontmatter and body. Then add one row to `projects/README.md`
(create the file with a header row if it does not yet exist):

```markdown
| Acronym | Funder | Institution | Status | Deadline | Amount | Folder |
```

**Step 6 — Confirm.**
Show the user the generated `index.md` and ask them to verify the auto-extracted fields
(title, funder, amount, period) before finishing.

**Step 7 — Verify layout (run after user confirms).**
Run the full "Verifying a project" workflow (see below) on the newly created project and show the compliance report to the user alongside the confirmation. This ensures the repo and SharePoint are consistent from the start.

---

### Answering a question about a project

Trigger: user asks anything about a specific project, or asks a cross-project question
(e.g. "what projects are due this year?", "summarise the PANTR science case").

**Cross-project questions (no document fetch needed)**

Read `projects/README.md` and all `index.md` files (frontmatter only is sufficient).
Answer directly from the structured metadata — do not fetch SharePoint documents.

**Project-specific questions about content**

1. If the project is not already identified, scan `projects/README.md` to find the best match.
2. Read `projects/<folder>/index.md`. The SharePoint Documents table stores each file's
   path relative to `sharepoint_folder` in the `File` column — reconstruct a document's
   URL on demand by concatenating `sharepoint_folder` with that value (see "`index.md`
   body convention").
3. Determine which document is most relevant to the question:
   - Science/approach questions → main proposal PDF/DOCX
   - Budget/cost questions → budget XLSX or budget section of proposal
   - Timeline/milestones → proposal or work-plan section
4. Download that document to `tmp/` via `sp.py` and extract its text (see step 3 of
   the "adding a grant" workflow for extraction commands).
5. Answer the question, citing the document and section where possible.
6. If the answer is not found in the first document, check the next most relevant file
   from the SharePoint Documents table before saying the information is unavailable.

---

### Verifying a project

Trigger: step 7 of "Adding a new project", or the user asks to verify / check / audit a
project's documents or layout.

The SharePoint Documents table in `index.md` is a cache of the live folder. This workflow
re-validates it against SharePoint and **reconciles** the table — it is the single source
of truth for the table's contents. It does **not** blindly overwrite: the `Document` label
column is human-curated (e.g. "Institutional Endorsement", "Verwertungsplan") and cannot be
re-derived from filenames, so labels are preserved.

**Step 1 — Determine the documents base.**
From `status` (see "Document location by status"):
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
Run the Required Documents check against the enumerated files and emit a missing-document
warning for each one not found (see "Warning format").

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
