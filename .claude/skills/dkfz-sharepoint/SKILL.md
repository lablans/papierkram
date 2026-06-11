---
name: dkfz-sharepoint
description: >
  Fetch files from DKFZ on-premise SharePoint servers (webcoop.inet.dkfz-heidelberg.de,
  intracoop.dkfz-heidelberg.de). Use when asked to download, read, list, or access
  files on DKFZ SharePoint / webcoop / intracoop.
---

# DKFZ SharePoint Fetch

Driver: `$GITREPO/.claude/skills/dkfz-sharepoint/sp.py`, lives within the `papierkram` git repo.
Auth: ADFS form-based via `feds.dkfz-heidelberg.de`; credentials from `rbw` (UUID supplied by user in .env file or env var).

## How it works

Authentication uses the SP-initiated WS-Federation passive flow:
1. GET ADFS login form at `feds.dkfz-heidelberg.de/adfs/ls/` with the SharePoint realm
2. POST credentials (`AD\<user>` + password) — ADFS returns a `wresult` form
3. POST `wresult` to SharePoint `/_trust/default.aspx` → `FedAuth` cookie
4. Use `FedAuth` for all subsequent requests (REST API or WebDAV)

Supported hosts:
- `webcoop.inet.dkfz-heidelberg.de`: Files are always in `https://webcoop.inet.dkfz-heidelberg.de/sites/verbis/`
- `intracoop.dkfz-heidelberg.de`: Files are always in `https://intracoop.dkfz-heidelberg.de/sites/verbis-int/`

## Prerequisites

```bash
pip install requests requests-ntlm beautifulsoup4 --break-system-packages
```
(`requests_ntlm` is already installed; `beautifulsoup4` was installed during skill creation.)

## Usage

### Download a file

```bash
python3 ~/.claude/skills/dkfz-sharepoint/sp.py \
  "https://webcoop.inet.dkfz-heidelberg.de/sites/verbis/GBA/.../file.docx"
```

With explicit output path:
```bash
python3 ~/.claude/skills/dkfz-sharepoint/sp.py \
  "https://webcoop.inet.dkfz-heidelberg.de/sites/.../file.docx" \
  -o /tmp/file.docx
```

### List a directory

```bash
python3 ~/.claude/skills/dkfz-sharepoint/sp.py --list \
  "https://webcoop.inet.dkfz-heidelberg.de/sites/verbis/GBA/GBN_21-23/Management/Berichte/Abschlussbericht%202026/"
```

A URL ending in `/` also triggers listing automatically.

### Show version history of a file

```bash
python3 ~/.claude/skills/dkfz-sharepoint/sp.py --versions \
  "https://webcoop.inet.dkfz-heidelberg.de/sites/verbis/pantr/2026/COHESION/COHESION_full.docx"
```

Prints each version with its label, creation timestamp, byte size, and author.
The current (latest) version is prefixed with `@` (e.g. `@2.0`).

### From Claude Code (typical agent use)

Use `Bash` with the commands above. After download, use `Read` or `Bash` to inspect content. For DOCX files, extract text with:

```bash
python3 -c "
import zipfile, re
with zipfile.ZipFile('/tmp/file.docx') as z:
    xml = z.read('word/document.xml').decode()
    text = re.sub(r'<[^>]+>', ' ', xml)
    text = re.sub(r' +', ' ', text)
    print(text[:5000])
"
```

## Verified examples

These commands were run and worked:

```
# List
python3 ~/.claude/skills/dkfz-sharepoint/sp.py --list \
  "https://webcoop.inet.dkfz-heidelberg.de/sites/verbis/GBA/GBN_21-23/Management/Berichte/Abschlussbericht%202026/"
# → [dir] Abschlussbericht 2026/
# → [file] GBN_01EY2001D_IT_Abschlussbericht.docx  (78990 bytes)
# → [file] Kurzbericht.docx  (52812 bytes)
# → ...

# Download
python3 ~/.claude/skills/dkfz-sharepoint/sp.py \
  "https://webcoop.inet.dkfz-heidelberg.de/sites/verbis/GBA/GBN_21-23/Management/Berichte/Abschlussbericht%202026/GBN_01EY2001D_IT_Abschlussbericht.docx" \
  -o /tmp/test.docx
# → Saved 78,990 bytes → /tmp/test.docx

# Version history
python3 ~/.claude/skills/dkfz-sharepoint/sp.py --versions \
  "https://webcoop.inet.dkfz-heidelberg.de/sites/verbis/pantr/2026/COHESION/COHESION_full.docx"
# → Version    Created                        Size  Created By
# → ---------------------------------------------------------------------------
# → @2.0       09.06.2026 16:34          2,059,281  Kussel, Tobias
# → 1.0        09.06.2026 16:33          2,059,281  Kussel, Tobias
```

## Gotchas

- **Username format must be `AD\<user>`**, not `<user>@dkfz-heidelberg.de` — the latter fails at the ADFS login form with "ID or password incorrect"
- **WS-Trust usernamemixed/windowsmixed endpoints are not usable** — usernamemixed returns ID3242, windowsmixed returns 503. Use the form-based passive flow (what this skill does).
- **NTLM alone isn't enough** — NTLM authenticates at the IIS level (userId=0 in SP page context) but SharePoint itself uses ADFS claims identity. You must go through the ADFS form flow.
- **rclone `vendor=sharepoint` hits Microsoft Online** — times out on the internal network; not usable for on-prem.
- **Realm is derived from the first hostname component**: `webcoop` → `urn:sharepoint:webcoop`, `intracoop` → `urn:sharepoint:intracoop`
- **FedAuth cookie is session-scoped** — re-authenticate for each new Python process; no persistent cookie store.
