---
name: dkfz-sharepoint
description: >
  Fetch files from DKFZ on-premise SharePoint servers (webcoop.inet.dkfz-heidelberg.de,
  intracoop.dkfz-heidelberg.de). Use when asked to download, read, list, or access
  files on DKFZ SharePoint / webcoop / intracoop.
---

# DKFZ SharePoint

Tool: `python3 .claude/skills/dkfz-sharepoint/sp.py` (in this repo; `--help` lists all options). Credentials come from `rbw`; if it is locked, ask the user to run `! rbw unlock`.

Files live under `https://webcoop.inet.dkfz-heidelberg.de/sites/verbis/` and `https://intracoop.dkfz-heidelberg.de/sites/verbis-int/`.

## Usage

```bash
# Download (-o is required; always into the session scratchpad). Also writes <output>.etag,
# the server version the copy came from, for a later upload with --base.
sp.py "https://webcoop.inet.dkfz-heidelberg.de/sites/verbis/.../file.docx" -o <scratchpad>/file.docx

# List a folder (a URL ending in / lists automatically)
sp.py --list "https://webcoop.inet.dkfz-heidelberg.de/sites/verbis/.../"

# Version history (the current version is marked @), and download of one version
sp.py --versions "https://…/file.docx"
sp.py --version 1.0 "https://…/file.docx" -o <scratchpad>/file_v1.docx
```

Uploads (`--upload`, dry run unless `--confirm`; updates need `--update --base <download>`) follow the upload policy in the repo's CLAUDE.md.

To read downloaded Office files, use the document skills named in CLAUDE.md.
