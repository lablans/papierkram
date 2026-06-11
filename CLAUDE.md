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

## Grant Repository Layout

```
grants/
├── README.md                        # master index table of all grants
├── active/
│   └── YYYY_FUNDER_ACRONYM/
│       └── index.md
├── submitted/
├── funded/
└── rejected/
```

Folder naming: `YYYY_FUNDER_ACRONYM` (e.g. `2025_DFG_PANTR`).

### `index.md` frontmatter convention

```yaml
---
title: "Full Official Grant Title"
funder: DFG                          # funding agency
program: SPP 2306                    # call / programme
acronym: PANTR
institution: DKFZ                    # DKFZ | UMM — which institution submits
role: PI                             # PI | Co-PI | Coordinator
status: active                       # active | submitted | funded | rejected
submitted: ~                         # ISO date or ~ if not yet
deadline: 2025-11-30
decision_expected: 2026-03-01
decision: ~
amount_requested: 450000             # EUR, direct costs excl. overhead
amount_granted: ~
period: 2025–2027
tags: [pancreatic-cancer, single-cell]
sharepoint_folder: https://webcoop.inet.dkfz-heidelberg.de/sites/verbis/pantr/
---
```

Fields `title`, `funder`, `program`, `amount_requested`, `period`, and the summary
paragraph are auto-generated from the proposal documents. The following must be
provided manually (not derivable from documents):

- `institution` — DKFZ or UMM
- `sharepoint_folder` — URL to the SharePoint directory
- `role` — your role on the grant
- `deadline`, `decision_expected` — from the call announcement
- `status`, `decision`, `amount_granted` — updated over the grant lifecycle

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

## Workflows

### Adding a new grant proposal

Trigger: user says "add a grant", "new proposal", or similar.

**Step 1 — Collect required inputs from the user.**
Ask for all fields that cannot be inferred from the proposal document. Ask them together in a single message, not one at a time:

- `sharepoint_folder` — URL to the SharePoint directory containing the proposal files
- `institution` — DKFZ or UMM
- `role` — PI, Co-PI, or Coordinator
- `deadline` — submission deadline (from the call announcement)
- `decision_expected` — when the funding decision is expected (optional)
- `status` — default `active` unless told otherwise

**Step 2 — Discover documents.**
If the user provides an `AllItems.aspx?id=...` SharePoint URL, convert it to a direct path URL first: URL-decode the `id` parameter value and use that as the path (append a trailing `/`). For example, `?id=%2Fsites%2Fverbis%2Fpantr%2F2026%2FCOHESION` → `https://webcoop.inet.dkfz-heidelberg.de/sites/verbis/pantr/2026/COHESION/`.

List the SharePoint folder using `sp.py --list <sharepoint_folder>`. Identify the main proposal file (largest PDF or DOCX, or one named "proposal"/"Antrag") and the budget file (XLSX or a clearly named PDF).

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
grants/<status>/YYYY_FUNDER_ACRONYM/index.md
```

Write `index.md` with the full frontmatter and body. Then add one row to `grants/README.md`
(create the file with a header row if it does not yet exist):

```markdown
| Acronym | Funder | Institution | Status | Deadline | Amount | Folder |
```

**Step 6 — Confirm.**
Show the user the generated `index.md` and ask them to verify the auto-extracted fields
(title, funder, amount, period) before finishing.

---

### Answering a question about a grant

Trigger: user asks anything about a specific grant, or asks a cross-grant question
(e.g. "what grants are due this year?", "summarise the PANTR science case").

**Cross-grant questions (no document fetch needed)**

Read `grants/README.md` and all `index.md` files (frontmatter only is sufficient).
Answer directly from the structured metadata — do not fetch SharePoint documents.

**Grant-specific questions about content**

1. If the grant is not already identified, scan `grants/README.md` to find the best match.
2. Read `grants/<status>/<folder>/index.md` to get the SharePoint document URLs.
3. Determine which document is most relevant to the question:
   - Science/approach questions → main proposal PDF/DOCX
   - Budget/cost questions → budget XLSX or budget section of proposal
   - Timeline/milestones → proposal or work-plan section
4. Download that document to `/tmp/` via `sp.py` and extract its text (see step 3 of
   the "adding a grant" workflow for extraction commands).
5. Answer the question, citing the document and section where possible.
6. If the answer is not found in the first document, check the next most relevant file
   from the SharePoint Documents table before saying the information is unavailable.
