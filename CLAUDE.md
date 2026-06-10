# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

This repo ("papierkram" — German for paperwork) is a Claude Code workspace for document tasks: reading, summarizing, and managing files that live on DKFZ SharePoint servers.

## SharePoint skill

The `dkfz-sharepoint` skill (`sp.py`) authenticates to DKFZ on-premise SharePoint via ADFS and supports listing directories and downloading files.

### Prerequisites

- `rbw` (Bitwarden CLI) must be unlocked; credentials are fetched from the UUID in `.env`
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

### Reading downloaded files

TODO: Don't reinvent the wheel -- find nice skill to deal with MS Office and PDF files.
