#!/usr/bin/env python3
"""
fetch_keys.py — Megacloud Decryption Key Fetcher
=================================================
Downloads the decryption keys.json from known upstream sources and stores
a local copy in keys/keys.json. This script is designed to be run by
GitHub Actions on a schedule so that RPDevs-Builds hosts its own mirror
of the keys, independent of any single upstream provider.

Exit codes:
  0 — Keys were updated (new content differs from existing).
  2 — No update needed (keys unchanged or all sources failed).
  1 — Fatal error.
"""
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

KEYS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "keys")
KEYS_FILE = os.path.join(KEYS_DIR, "keys.json")

# ---------------------------------------------------------------------------
# Upstream sources to try, in priority order.
# If the primary is DMCA'd or offline, we fall through to alternates.
# Community members can add new mirrors here via PR.
# ---------------------------------------------------------------------------
UPSTREAM_SOURCES = [
    # Primary: Original yogesh-hacker repo (currently DMCA'd / 451)
    "https://raw.githubusercontent.com/yogesh-hacker/MegacloudKeys/main/keys.json",
    "https://raw.githubusercontent.com/yogesh-hacker/MegacloudKeys/refs/heads/main/keys.json",
]

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64; rv:133.0) Gecko/20100101 Firefox/133.0"


def fetch_from_url(url: str) -> dict | None:
    """Attempt to download and parse keys.json from a single URL."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            # Validate: must contain the 'vidstr' key with a non-empty value
            if data.get("vidstr"):
                return data
            else:
                print(f"  [WARN] {url} — missing or empty 'vidstr' key")
    except Exception as e:
        print(f"  [FAIL] {url} — {e}")
    return None


def load_existing_keys() -> dict | None:
    """Load the currently stored keys.json, if it exists."""
    if os.path.isfile(KEYS_FILE):
        try:
            with open(KEYS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return None


def save_keys(keys: dict) -> None:
    """Write keys to disk with RPDevs metadata."""
    os.makedirs(KEYS_DIR, exist_ok=True)
    output = {
        "vidstr": keys["vidstr"],
        "_meta": {
            "source": "https://github.com/RPDevs-Builds/script.service.megacloud",
            "description": "Megacloud decryption keys. Auto-updated by GitHub Actions.",
            "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
    }
    with open(KEYS_FILE, "w") as f:
        json.dump(output, f, indent=2)
        f.write("\n")
    print(f"  [OK] Saved keys to {KEYS_FILE}")


def main():
    print("=== Megacloud Key Fetcher ===")

    # Try each upstream source in order
    fetched_keys = None
    for url in UPSTREAM_SOURCES:
        print(f"Trying: {url}")
        fetched_keys = fetch_from_url(url)
        if fetched_keys:
            print(f"  [OK] Got valid keys from {url}")
            break

    if not fetched_keys:
        print("\n[WARN] All upstream sources failed. Keys NOT updated.")
        print("       Add new mirror URLs to UPSTREAM_SOURCES in this script.")
        sys.exit(2)

    # Compare with existing
    existing = load_existing_keys()
    if existing and existing.get("vidstr") == fetched_keys.get("vidstr"):
        print("\n[INFO] Keys unchanged — no update needed.")
        sys.exit(2)

    # Save the new keys
    save_keys(fetched_keys)
    print("\n[OK] Keys updated successfully.")
    sys.exit(0)


if __name__ == "__main__":
    main()
