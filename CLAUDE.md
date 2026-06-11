# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

This repo ("papierkram" — German for paperwork) is a Claude Code workspace for document tasks: reading, summarizing, and managing files that live on DKFZ SharePoint servers.

## SharePoint skill

The `dkfz-sharepoint` skill (`sp.py`) authenticates to DKFZ on-premise SharePoint via ADFS and supports listing directories and downloading files.

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
  -o /tmp/somefile.docx
```

A URL ending in `/` triggers listing automatically.

### Known site prefixes

| Server | Base URL |
|--------|----------|
| webcoop | `https://webcoop.inet.dkfz-heidelberg.de/sites/verbis/` |
| intracoop | `https://intracoop.dkfz-heidelberg.de/` |

### Versioning

SharePoint's built-in versioning is the only versioning mechanism — files keep their canonical filename on SharePoint. Never upload or instruct the user to save `_v1`, `_v2`, `_old`, etc. suffixed copies to SharePoint. If the user does this, tell them off and remind them to delete the duplicates. Locally (e.g. `/tmp/`), use `_v1`/`_v2` suffixes matching the SharePoint version label when downloading multiple versions for comparison.

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

| Document | Type | URL |
|---|---|---|
| Full Proposal | PDF | https://webcoop.../proposal.pdf |
| Budget Table | XLSX | https://webcoop.../budget.xlsx |

## Key Contacts

## Notes
```

## Required Documents

Every project must have specific documents on SharePoint. **Whenever you read or create a project `index.md`, run the completeness check below and emit a warning for every missing required document** — do not wait for the user to ask.

### Document requirements by status and funder

| Document | Required when | Keywords / naming hints |
|---|---|---|
| Budget table | always | "budget", "Kosten", "Finanzplan", "Kalkulation"; `.xlsx`/`.xls` extension |
| Proposal text / Part B | always | "proposal", "Antrag", "Part_B", "PartB", "Teil_B", "full" |
| Grants office checklist | always | "checklist", "Checkliste" |
| Part A — applicant info | EU projects (funder: EC, EU, ERC, or similar) | "Part_A", "PartA", "Teil_A", "administrative" |
| AZAP | once submitted (`submitted:` field is a date, not `~`) | "AZAP" |

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
Download the main proposal document to `/tmp/` via `sp.py`. Extract its text using existing skills to read pdf and microsoft office files.

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
Run the full "Verify project" workflow (see below) on the newly created project and show the compliance report to the user alongside the confirmation. This ensures the repo and SharePoint are consistent from the start.

---

### Answering a question about a project

Trigger: user asks anything about a specific project, or asks a cross-project question
(e.g. "what projects are due this year?", "summarise the PANTR science case").

**Cross-project questions (no document fetch needed)**

Read `projects/README.md` and all `index.md` files (frontmatter only is sufficient).
Answer directly from the structured metadata — do not fetch SharePoint documents.

**Project-specific questions about content**

1. If the project is not already identified, scan `projects/README.md` to find the best match.
2. Read `projects/<folder>/index.md` to get the SharePoint document URLs.
3. Determine which document is most relevant to the question:
   - Science/approach questions → main proposal PDF/DOCX
   - Budget/cost questions → budget XLSX or budget section of proposal
   - Timeline/milestones → proposal or work-plan section
4. Download that document to `/tmp/` via `sp.py` and extract its text (see step 3 of
   the "adding a grant" workflow for extraction commands).
5. Answer the question, citing the document and section where possible.
6. If the answer is not found in the first document, check the next most relevant file
   from the SharePoint Documents table before saying the information is unavailable.
