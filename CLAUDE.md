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

### After a successful upload, do not re-verify

`sp.py` exits non-zero (printing `Error: PUT returned <code>`) on failure and
prints `Updated`/`Uploaded … (HTTP 200/201)` only on success. That success line
**is** authoritative confirmation that SharePoint accepted the write — do **not**
re-download the file to check it.

A round-trip hash comparison is in fact misleading: SharePoint re-processes Office
files on save (injecting document-management metadata into `customXml`/`docProps`),
so the re-downloaded copy always has a different outer byte hash even when the
content is byte-for-byte intact. The pre-upload content comparison (above) is the
only content check needed.

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
| Grants office checklist | DKFZ projects only (`institution: DKFZ`) | "checklist", "Checkliste" | `Checklist.docx`, `Checklist.pdf` |
| Part A — applicant info | EU projects (funder: EC, EU, ERC, or similar) | "Part_A", "PartA", "Teil_A", "administrative", "Info Collector", "InfoCollect"; contains PIC number of the institution | ~ |
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

### Adding or updating a project

Triggers: "add a grant", "new proposal", "new project", "update project info", "update a project".
Invoke the `add-project` skill.

### Answering a question about a project

For cross-project questions ("what projects are due this year?"), read `projects/README.md` and all `index.md` frontmatter — no SharePoint fetch needed.

For project-specific content questions, read `projects/<folder>/index.md`, reconstruct the document URL by concatenating `sharepoint_folder` with the relative `File` value, download the most relevant document to `tmp/` via `sp.py`, and answer citing the section. Route by type: science/approach → proposal PDF/DOCX; budget/costs → budget XLSX; timeline/milestones → work-plan section. If the answer is not in the first document, try the next most relevant file before saying it's unavailable.

### Verifying a project

Triggers: step 7 of add-project, "verify project", "check project", "audit project", "update a project".
Invoke the `verify-project` skill.
