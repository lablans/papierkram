#!/usr/bin/env python3
"""Fetch files from DKFZ SharePoint (webcoop / intracoop) via ADFS auth."""

set_euo = None  # Python equivalent: errors exit immediately via sys.exit

import sys, subprocess, os, argparse
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
        "<D:prop><D:displayname/><D:resourcetype/><D:getcontentlength/></D:prop>"
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
        is_dir = resp.find(".//D:collection", ns) is not None
        if name:
            entries.append((is_dir, name, size or ""))

    # Dirs first, then files, each alphabetically
    for is_dir, name, size in sorted(entries, key=lambda x: (not x[0], x[1].lower())):
        suffix = "/" if is_dir else f"  ({size} bytes)" if size else ""
        print(f"{name}{suffix}")


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
    args = p.parse_args()

    username, password = get_credentials()

    if args.list or args.url.endswith("/"):
        cmd_list(args.url, username, password)
    else:
        cmd_download(args.url, args.output, username, password)


if __name__ == "__main__":
    if RBW_UUID is None:
        print("Error: DKFZ_SP_RBW_UUID environment variable not set. Ask the user to create an .env file with DKFZ_SP_RBW_UUID=<UUID>, with UUID being the UUID of their DKFZ account in Bitwarden (reachable via rbw).", file=sys.stderr)
        sys.exit(1)
    main()
