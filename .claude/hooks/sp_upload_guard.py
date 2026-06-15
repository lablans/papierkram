#!/usr/bin/env python3
"""PreToolUse gate (H2) for SharePoint writes via dkfz-sharepoint sp.py.

This hook is the SOLE approval gate for uploads (there is no backing `ask`
rule, so the hook's permissionDecisionReason is what renders in the prompt).
For any Bash command that runs sp.py with --confirm (the flag that actually
transmits a write), it returns permissionDecision "ask" with a dynamic reason
that names the destination and whether this creates or updates a file, so the
approval is an informed check rather than boilerplate. Reads and dry-runs pass
through untouched.
"""
import sys, json, re
from urllib.parse import unquote, urlparse

# Extract the URL straight from the raw command — independent of shell quoting,
# line continuations, or tokenisation. Stops at whitespace, quotes, backslash.
_URL_RE = re.compile(r'https?://[^\s"\'\\]+')
_UPDATE_RE = re.compile(r'(?:^|\s)--update(?:\s|$)')


def _build_reason(cmd):
    """Describe the write for the approval prompt; fall back to a generic note.

    Create vs Update is keyed on the --update flag: sp.py is create-only by
    default and requires --update to write onto an existing file, so --update
    present means an update (new version), absent means a new file.
    """
    action = "Update" if _UPDATE_RE.search(cmd) else "Create"
    m = _URL_RE.search(cmd)

    if not m:
        return ("SharePoint write (sp.py --confirm): verify the destination, "
                "create-vs-update, and filename before approving.")

    p = urlparse(m.group(0))
    host = (p.hostname or "").split(".")[0] or p.netloc
    segments = [s for s in unquote(p.path).split("/") if s]
    filename = segments[-1] if segments else unquote(p.path)
    parent_segs = segments[:-1]
    # Drop the SharePoint site-collection prefix (e.g. /sites/verbis) for brevity.
    if len(parent_segs) >= 2 and parent_segs[0].lower() == "sites":
        parent_segs = parent_segs[2:]
    parent = "/" + "/".join(parent_segs) if parent_segs else "/"

    return (f"⚠️ {action} {filename} in {host}:{parent}"
            f" — verify destination and filename before approving.")


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)  # never block on a parse error

    if data.get("tool_name") != "Bash":
        sys.exit(0)

    cmd = (data.get("tool_input") or {}).get("command", "")
    # Match on sp.py + --confirm (not the full path) so the gate still fires
    # for e.g. `cd .../dkfz-sharepoint && python3 sp.py ... --confirm`.
    if "sp.py" in cmd and "--confirm" in cmd:
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "ask",
                "permissionDecisionReason": _build_reason(cmd),
            }
        }))

    sys.exit(0)


if __name__ == "__main__":
    main()
