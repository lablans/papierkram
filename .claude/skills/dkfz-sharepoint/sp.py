#!/usr/bin/env python3
"""Fetch files from DKFZ SharePoint (webcoop / intracoop) via ADFS auth."""
import sys; sys.dont_write_bytecode = True

set_euo = None  # Python equivalent: errors exit immediately via sys.exit

import sys, subprocess, os, argparse, json, hashlib
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from dotenv import load_dotenv
load_dotenv()
from urllib.parse import urlparse, unquote

import requests
import html as htmlmod
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET

ADFS_HOST = "https://feds.dkfz-heidelberg.de"
RBW_UUID = os.environ.get("DKFZ_SP_RBW_UUID")
CACHE_DIR = "/tmp/papierkram"
SUPPORTED_HOSTS = {
    "webcoop",
    "webcoop.inet.dkfz-heidelberg.de",
    "intracoop",
    "intracoop.dkfz-heidelberg.de",
}

# --- Write-path safeguards (uploads only) ---------------------------------
# D4: uploads are refused unless the destination starts with one of these
# prefixes. Override with DKFZ_SP_WRITE_ALLOW_PREFIXES (comma-separated).
DEFAULT_WRITE_PREFIXES = (
    "https://webcoop.inet.dkfz-heidelberg.de/sites/verbis/pantr/",
)
# D9: append-only audit trail of every actual upload attempt, kept next to
# this script (gitignored).
AUDIT_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads.log")


def _write_allow_prefixes():
    env = os.environ.get("DKFZ_SP_WRITE_ALLOW_PREFIXES")
    if env:
        return tuple(p.strip() for p in env.split(",") if p.strip())
    return DEFAULT_WRITE_PREFIXES


def _audit(record):
    """D9: append one JSON line per upload attempt. Best-effort, never fatal."""
    try:
        with open(AUDIT_LOG, "a") as f:
            f.write(json.dumps(record) + "\n")
    except OSError:
        pass


def _cache_path(sp_host):
    key = urlparse(sp_host).hostname.split(".")[0]
    return os.path.join(CACHE_DIR, f"fedauth_{key}.json")


def _load_cached_session(sp_host):
    try:
        with open(_cache_path(sp_host)) as f:
            data = json.load(f)
        sess = requests.Session()
        sess.cookies.set("FedAuth", data["FedAuth"], domain=urlparse(sp_host).hostname, path="/")
        return sess
    except (FileNotFoundError, KeyError, json.JSONDecodeError):
        return None


def _save_session_cache(sp_host, session):
    cookie = session.cookies.get("FedAuth")
    if not cookie:
        return
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(_cache_path(sp_host), "w") as f:
        json.dump({"FedAuth": cookie}, f)


def _clear_session_cache(sp_host):
    try:
        os.remove(_cache_path(sp_host))
    except FileNotFoundError:
        pass


def get_credentials():
    user = subprocess.check_output(["rbw", "get", RBW_UUID, "-f", "username"]).decode().strip()
    pw = subprocess.check_output(["rbw", "get", RBW_UUID, "-f", "password"]).decode().strip()
    return user, pw


def authenticate(sp_host, username, password, force=False):
    """Return an authenticated requests.Session with FedAuth cookie for sp_host."""
    if not force:
        cached = _load_cached_session(sp_host)
        if cached:
            return cached

    realm_key = urlparse(sp_host).hostname.split(".")[0]  # e.g. "webcoop"
    realm = f"urn%3asharepoint%3a{realm_key}"
    session = requests.Session()

    adfs_url = (
        f"{ADFS_HOST}/adfs/ls/?wa=wsignin1.0"
        f"&wtrealm={realm}"
        f"&wctx={requests.utils.quote(sp_host)}"
        f"&wreply={requests.utils.quote(sp_host + '/_trust/default.aspx')}"
    )

    # Step 1: GET ADFS login form
    r = session.get(adfs_url)
    soup = BeautifulSoup(r.text, "html.parser")
    form = soup.find("form")
    if not form:
        raise RuntimeError(f"No login form at ADFS ({r.status_code})")

    payload = {
        i.get("name"): htmlmod.unescape(i.get("value", ""))
        for i in form.find_all("input")
        if i.get("name")
    }
    payload["UserName"] = f"AD\\{username}"
    payload["Password"] = password

    action = form.get("action", "")
    if action.startswith("/"):
        action = ADFS_HOST + action

    # Step 2: POST credentials → ADFS returns redirect with wresult form
    r2 = session.post(action, data=payload, allow_redirects=True)
    soup2 = BeautifulSoup(r2.text, "html.parser")
    hidden = {
        i.get("name"): htmlmod.unescape(i.get("value", ""))
        for i in soup2.find_all("input", {"type": "hidden"})
    }

    if "wresult" not in hidden:
        raise RuntimeError("ADFS did not return wresult — credentials wrong or ADFS issue")

    # Step 3: POST wresult to SharePoint _trust → get FedAuth cookie
    form2 = soup2.find("form")
    action2 = form2.get("action", "") if form2 else f"{sp_host}/_trust/default.aspx"
    session.post(action2, data=hidden, allow_redirects=True)

    if "FedAuth" not in session.cookies:
        raise RuntimeError("No FedAuth cookie after _trust exchange — check SP realm config")

    _save_session_cache(sp_host, session)
    return session


def _get_session(sp_host, username, password, force=False):
    """Return a session, busting the cache and re-authing if force=True."""
    if force:
        _clear_session_cache(sp_host)
    return authenticate(sp_host, username, password, force=force)


def sp_host_from_url(url):
    p = urlparse(url)
    return f"{p.scheme}://{p.netloc}"


def cmd_list(url, username, password):
    """List contents of a SharePoint directory via WebDAV PROPFIND."""
    sp_host = sp_host_from_url(url)

    propfind_body = (
        '<?xml version="1.0"?>'
        '<D:propfind xmlns:D="DAV:">'
        "<D:prop><D:displayname/><D:resourcetype/><D:getcontentlength/><D:getlastmodified/></D:prop>"
        "</D:propfind>"
    )
    for attempt in range(2):
        sess = _get_session(sp_host, username, password, force=(attempt > 0))
        r = sess.request(
            "PROPFIND", url,
            headers={"Depth": "1", "Content-Type": "application/xml"},
            data=propfind_body,
        )
        if r.status_code == 403 and attempt == 0:
            continue
        break
    if r.status_code != 207:
        print(f"Error: PROPFIND returned {r.status_code}", file=sys.stderr)
        sys.exit(1)

    ns = {"D": "DAV:"}
    root = ET.fromstring(r.content)
    entries = []
    for resp in root.findall("D:response", ns):
        name = resp.findtext(".//D:displayname", "", ns)
        size = resp.findtext(".//D:getcontentlength", "", ns)
        modified_raw = resp.findtext(".//D:getlastmodified", "", ns)
        is_dir = resp.find(".//D:collection", ns) is not None
        if name:
            try:
                modified = parsedate_to_datetime(modified_raw).strftime("%Y-%m-%d %H:%M") if modified_raw else ""
            except Exception:
                modified = modified_raw
            entries.append((is_dir, name, size or "", modified))

    # Dirs first, then files, each alphabetically
    for is_dir, name, size, modified in sorted(entries, key=lambda x: (not x[0], x[1].lower())):
        if is_dir:
            mod_str = f"  {modified}" if modified else ""
            print(f"{name}/{mod_str}")
        else:
            parts = []
            if modified:
                parts.append(modified)
            if size:
                parts.append(f"{int(size):,} bytes")
            meta = f"  ({', '.join(parts)})" if parts else ""
            print(f"{name}{meta}")


def _resolve_display_name(sess, sp_host, site_path, login):
    """Return 'Last, First' display name for a SharePoint login, or the raw login on failure."""
    from urllib.parse import quote as urlquote
    url = (
        f"{sp_host}{site_path}/_api/SP.UserProfiles.PeopleManager"
        f"/GetPropertiesFor(accountName=@v)?@v='{urlquote(login)}'"
    )
    try:
        r = sess.get(url, headers={"Accept": "application/json;odata=verbose"}, timeout=10)
        if r.status_code == 200:
            name = r.json().get("d", {}).get("DisplayName", "")
            if name:
                return name
    except Exception:
        pass
    # Fall back to stripping the claims prefix
    return login.replace("i:0e.t|adfs|", "").replace("i:0#.w|ad\\", "")


def cmd_versions(url, username, password):
    """List version history of a SharePoint file via Versions.asmx SOAP."""
    sp_host = sp_host_from_url(url)
    parsed = urlparse(url)
    file_rel = unquote(parsed.path)

    # Versions.asmx must be called at the site level (e.g. /sites/verbis)
    parts = file_rel.strip("/").split("/")
    site_path = "/" + "/".join(parts[:2]) if len(parts) >= 2 and parts[0] == "sites" else ""

    soap_url = f"{sp_host}{site_path}/_vti_bin/Versions.asmx"
    soap_body = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
               xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
               xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <soap:Body>
    <GetVersions xmlns="http://schemas.microsoft.com/sharepoint/soap/">
      <fileName>{file_rel}</fileName>
    </GetVersions>
  </soap:Body>
</soap:Envelope>"""
    headers = {
        "Content-Type": "text/xml; charset=utf-8",
        "SOAPAction": '"http://schemas.microsoft.com/sharepoint/soap/GetVersions"',
    }

    for attempt in range(2):
        sess = _get_session(sp_host, username, password, force=(attempt > 0))
        r = sess.post(soap_url, data=soap_body, headers=headers)
        if r.status_code == 403 and attempt == 0:
            continue
        break
    if r.status_code != 200:
        print(f"Error: Versions.asmx returned {r.status_code}", file=sys.stderr)
        sys.exit(1)

    root = ET.fromstring(r.content)
    ns = "http://schemas.microsoft.com/sharepoint/soap/"
    items = list(root.iter(f"{{{ns}}}result"))
    if not items:
        print("No version history found.")
        return

    # Resolve each unique login to a display name (cached)
    name_cache = {}
    def display(login):
        if login not in name_cache:
            name_cache[login] = _resolve_display_name(sess, sp_host, site_path, login)
        return name_cache[login]

    print(f"{'Version':<10} {'Created':<22} {'Size':>12}  Created By")
    print("-" * 75)
    for elem in items:
        ver  = elem.get("version", "")
        date = elem.get("created", "")[:19].replace("T", " ")
        size = elem.get("size", "")
        by   = display(elem.get("createdBy", ""))
        print(f"{ver:<10} {date:<22} {int(size):>12,}  {by}" if size else f"{ver:<10} {date:<22} {'':>12}  {by}")


def _get_version_url(url, version_label, sess):
    """Return the download URL for a specific version label (e.g. '1.0') of a file."""
    sp_host = sp_host_from_url(url)
    parsed = urlparse(url)
    file_rel = unquote(parsed.path)
    parts = file_rel.strip("/").split("/")
    site_path = "/" + "/".join(parts[:2]) if len(parts) >= 2 and parts[0] == "sites" else ""

    soap_url = f"{sp_host}{site_path}/_vti_bin/Versions.asmx"
    soap_body = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
               xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
               xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <soap:Body>
    <GetVersions xmlns="http://schemas.microsoft.com/sharepoint/soap/">
      <fileName>{file_rel}</fileName>
    </GetVersions>
  </soap:Body>
</soap:Envelope>"""
    r = sess.post(
        soap_url, data=soap_body,
        headers={"Content-Type": "text/xml; charset=utf-8",
                 "SOAPAction": '"http://schemas.microsoft.com/sharepoint/soap/GetVersions"'},
    )
    if r.status_code != 200:
        print(f"Error: Versions.asmx returned {r.status_code}", file=sys.stderr)
        sys.exit(1)
    ns = "http://schemas.microsoft.com/sharepoint/soap/"
    root = ET.fromstring(r.content)
    for elem in root.iter(f"{{{ns}}}result"):
        ver = elem.get("version", "").lstrip("@")
        if ver == version_label:
            return elem.get("url")
    return None


def cmd_download(url, output, username, password, version_label=None):
    """Download a file from SharePoint, optionally a specific version."""
    sp_host = sp_host_from_url(url)

    for attempt in range(2):
        sess = _get_session(sp_host, username, password, force=(attempt > 0))
        if version_label:
            versioned_url = _get_version_url(url, version_label, sess)
            if not versioned_url:
                print(f"Error: version '{version_label}' not found", file=sys.stderr)
                sys.exit(1)
            download_url = versioned_url
        else:
            download_url = url
        r = sess.get(download_url, allow_redirects=True)
        if r.status_code == 403 and attempt == 0:
            continue
        break
    if r.status_code != 200:
        print(f"Error: {r.status_code}", file=sys.stderr)
        sys.exit(1)

    if not output:
        output = unquote(urlparse(url).path.rstrip("/").split("/")[-1])
    if not output:
        output = "download"

    with open(output, "wb") as f:
        f.write(r.content)

    print(f"Saved {len(r.content):,} bytes → {output}")


def _target_status(sess, url):
    """PROPFIND Depth:0 on a target URL. Returns the HTTP status code."""
    body = (
        '<?xml version="1.0"?>'
        '<D:propfind xmlns:D="DAV:"><D:prop><D:resourcetype/></D:prop></D:propfind>'
    )
    r = sess.request(
        "PROPFIND", url,
        headers={"Depth": "0", "Content-Type": "application/xml"},
        data=body,
    )
    return r.status_code


def cmd_upload(local_path, url, username, password, confirm=False, update=False):
    """Upload a local file to SharePoint via WebDAV PUT, behind safeguards.

    D1 this is a separate, explicit mode (never inferred).
    D2 dry-run by default; nothing is transmitted without --confirm.
    D3 create-only by default; updating an existing file requires --update.
    D4 destination must lie under an allowed write prefix.
    D9 every actual attempt is appended to the audit log.
    """
    sp_host = sp_host_from_url(url)

    # D4: write-path allowlist — refuse anything outside the allowed roots.
    prefixes = _write_allow_prefixes()
    if not any(url.startswith(pre) for pre in prefixes):
        print(
            "Error: upload destination is not within an allowed write prefix.\n"
            f"  destination: {url}\n"
            f"  allowed    : {', '.join(prefixes)}",
            file=sys.stderr,
        )
        sys.exit(2)

    if not os.path.isfile(local_path):
        print(f"Error: local file not found: {local_path}", file=sys.stderr)
        sys.exit(2)

    with open(local_path, "rb") as f:
        data = f.read()
    sha = hashlib.sha256(data).hexdigest()
    size = len(data)

    # Probe whether the target already exists (needs auth; retry once on 403).
    for attempt in range(2):
        sess = _get_session(sp_host, username, password, force=(attempt > 0))
        code = _target_status(sess, url)
        if code == 403 and attempt == 0:
            continue
        break

    if code == 207:
        exists = True
    elif code == 404:
        exists = False
    else:
        # Ambiguous — refuse to guess rather than risk clobbering.
        print(
            f"Error: could not determine whether the target exists "
            f"(PROPFIND returned {code}). Aborting for safety.",
            file=sys.stderr,
        )
        sys.exit(4)

    action = "update (adds a new SharePoint version)" if exists else "create new file"
    print("-- SharePoint upload ---------------------------------------------")
    print(f"  source       : {local_path}")
    print(f"  size         : {size:,} bytes")
    print(f"  sha256       : {sha}")
    print(f"  destination  : {url}")
    print(f"  target exists: {'YES' if exists else 'no'}")
    print(f"  action       : {action}")
    print("------------------------------------------------------------------")

    # D2: dry-run unless --confirm.
    if not confirm:
        print("DRY RUN - nothing was sent. Re-run with --confirm to upload.")
        return

    # D3: create-only unless --update.
    if exists and not update:
        print(
            "Error: target already exists; uploading would add a new version.\n"
            "       Re-run with --update to confirm updating the existing file.",
            file=sys.stderr,
        )
        sys.exit(3)

    # Transmit (retry once on 403).
    for attempt in range(2):
        sess = _get_session(sp_host, username, password, force=(attempt > 0))
        r = sess.put(url, data=data)
        if r.status_code == 403 and attempt == 0:
            continue
        break

    ok = r.status_code in (200, 201, 204)
    _audit({
        "ts": datetime.now(timezone.utc).isoformat(),
        "user": username,
        "source": os.path.abspath(local_path),
        "sha256": sha,
        "size": size,
        "destination": url,
        "existed": exists,
        "status": r.status_code,
        "result": "ok" if ok else "error",
    })

    if not ok:
        print(f"Error: PUT returned {r.status_code}", file=sys.stderr)
        sys.exit(1)

    verb = "Updated" if exists else "Uploaded"
    print(f"{verb} {size:,} bytes -> {url}  (HTTP {r.status_code})")


def main():
    p = argparse.ArgumentParser(
        description="Fetch files from DKFZ SharePoint (webcoop/intracoop)"
    )
    p.add_argument("url", help="Full SharePoint URL (file or folder)")
    p.add_argument("-o", "--output", help="Output path for downloaded file")
    p.add_argument(
        "--list", action="store_true",
        help="List directory contents instead of downloading",
    )
    p.add_argument(
        "--versions", action="store_true",
        help="Show version history of a file",
    )
    p.add_argument(
        "--version",
        metavar="LABEL",
        help="Download a specific version (e.g. 1.0); use with download mode",
    )
    p.add_argument(
        "--upload",
        metavar="LOCALFILE",
        help="Upload LOCALFILE to the destination URL (dry-run unless --confirm)",
    )
    p.add_argument(
        "--confirm", action="store_true",
        help="Actually transmit the upload (without it, --upload is a dry run)",
    )
    p.add_argument(
        "--update", action="store_true",
        help="Allow upload to an existing file (adds a new version); else create-only",
    )
    args = p.parse_args()

    username, password = get_credentials()

    if args.upload:
        cmd_upload(
            args.upload, args.url, username, password,
            confirm=args.confirm, update=args.update,
        )
    elif args.versions:
        cmd_versions(args.url, username, password)
    elif args.list or args.url.endswith("/"):
        cmd_list(args.url, username, password)
    else:
        cmd_download(args.url, args.output, username, password, version_label=args.version)


if __name__ == "__main__":
    if RBW_UUID is None:
        print("Error: DKFZ_SP_RBW_UUID environment variable not set. Ask the user to create an .env file with DKFZ_SP_RBW_UUID=<UUID>, with UUID being the UUID of their DKFZ account in Bitwarden (reachable via rbw).", file=sys.stderr)
        sys.exit(1)
    main()
