#!/usr/bin/env python3
"""Fetch files from DKFZ SharePoint (webcoop / intracoop) via ADFS auth."""
import sys; sys.dont_write_bytecode = True

set_euo = None  # Python equivalent: errors exit immediately via sys.exit

import sys, subprocess, os, argparse
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
SUPPORTED_HOSTS = {
    "webcoop",
    "webcoop.inet.dkfz-heidelberg.de",
    "intracoop",
    "intracoop.dkfz-heidelberg.de",
}


def get_credentials():
    user = subprocess.check_output(["rbw", "get", RBW_UUID, "-f", "username"]).decode().strip()
    pw = subprocess.check_output(["rbw", "get", RBW_UUID, "-f", "password"]).decode().strip()
    return user, pw


def authenticate(sp_host, username, password):
    """Return an authenticated requests.Session with FedAuth cookie for sp_host."""
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

    return session


def sp_host_from_url(url):
    p = urlparse(url)
    return f"{p.scheme}://{p.netloc}"


def cmd_list(url, username, password):
    """List contents of a SharePoint directory via WebDAV PROPFIND."""
    sp_host = sp_host_from_url(url)
    sess = authenticate(sp_host, username, password)

    propfind_body = (
        '<?xml version="1.0"?>'
        '<D:propfind xmlns:D="DAV:">'
        "<D:prop><D:displayname/><D:resourcetype/><D:getcontentlength/><D:getlastmodified/></D:prop>"
        "</D:propfind>"
    )
    r = sess.request(
        "PROPFIND", url,
        headers={"Depth": "1", "Content-Type": "application/xml"},
        data=propfind_body,
    )
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
    return login.replace("i:0e.t|adfs|", "").replace("i:0#.w|ad\\", "")


def cmd_versions(url, username, password):
    """List version history of a SharePoint file via Versions.asmx SOAP."""
    sp_host = sp_host_from_url(url)
    parsed = urlparse(url)
    file_rel = unquote(parsed.path)

    # Versions.asmx must be called at the site level (e.g. /sites/verbis)
    parts = file_rel.strip("/").split("/")
    site_path = "/" + "/".join(parts[:2]) if len(parts) >= 2 and parts[0] == "sites" else ""

    sess = authenticate(sp_host, username, password)

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
        soap_url,
        data=soap_body,
        headers={
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": '"http://schemas.microsoft.com/sharepoint/soap/GetVersions"',
        },
    )
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


def cmd_download(url, output, username, password):
    """Download a file from SharePoint."""
    sp_host = sp_host_from_url(url)
    sess = authenticate(sp_host, username, password)

    r = sess.get(url, allow_redirects=True)
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
    args = p.parse_args()

    username, password = get_credentials()

    if args.versions:
        cmd_versions(args.url, username, password)
    elif args.list or args.url.endswith("/"):
        cmd_list(args.url, username, password)
    else:
        cmd_download(args.url, args.output, username, password)


if __name__ == "__main__":
    if RBW_UUID is None:
        print("Error: DKFZ_SP_RBW_UUID environment variable not set. Ask the user to create an .env file with DKFZ_SP_RBW_UUID=<UUID>, with UUID being the UUID of their DKFZ account in Bitwarden (reachable via rbw).", file=sys.stderr)
        sys.exit(1)
    main()
