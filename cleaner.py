#!/usr/bin/env python3
"""
komoot-cleaner: delete all recorded tours from a Komoot account.

Authentication uses Komoot's undocumented Basic-Auth endpoint:
  GET https://api.komoot.de/v006/account/email/{email}
  Authorization: Basic base64(email:password)
  → returns { username, password }  (numeric user-id and API token)

Subsequent calls use:
  Authorization: Basic base64(userId:token)
"""

import os
import sys
import time
import base64
import logging

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

API_V006 = "https://api.komoot.de/v006"
API_V007 = "https://api.komoot.de/v007"
DELETE_DELAY = 0.15  # seconds between DELETE calls


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def _basic(user: str, password: str) -> str:
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return f"Basic {token}"


def login(email: str, password: str) -> tuple[str, str]:
    """Return (user_id, api_token) for the given credentials."""
    url = f"{API_V006}/account/email/{requests.utils.quote(email, safe='')}"
    resp = requests.get(url, headers={"Authorization": _basic(email, password)})
    if resp.status_code in (401, 403):
        log.error("Login failed (HTTP %s): wrong email or password.", resp.status_code)
        sys.exit(1)
    resp.raise_for_status()
    data = resp.json()
    user_id = str(data["username"])
    api_token = data["password"]
    log.info("Logged in as %s (id=%s)", data.get("displayName", email), user_id)
    return user_id, api_token


# ---------------------------------------------------------------------------
# Tour listing
# ---------------------------------------------------------------------------

def list_recorded_tours(user_id: str, auth_header: str) -> list[dict]:
    """Return all recorded tours as a list of dicts with at least {id, name}."""
    tours: list[dict] = []
    url = f"{API_V007}/users/{user_id}/tours/?type=recorded&page=0&limit=50"

    while url:
        resp = requests.get(url, headers={"Authorization": auth_header})
        resp.raise_for_status()
        data = resp.json()

        embedded = data.get("_embedded", {})
        page_tours = embedded.get("tours", [])
        for t in page_tours:
            tour_type = t.get("type", "")
            if tour_type != "recorded_route":
                log.warning(
                    "Skipping tour %s (%r) — type=%r is not 'recorded_route'",
                    t["id"], t.get("name", ""), tour_type,
                )
                continue
            tours.append({"id": str(t["id"]), "name": t.get("name", "(unnamed)")})

        url = data.get("_links", {}).get("next", {}).get("href")

    return tours


# ---------------------------------------------------------------------------
# Deletion
# ---------------------------------------------------------------------------

def delete_tour(tour_id: str, auth_header: str, dry_run: bool) -> bool:
    """Delete a single tour. Returns True on success."""
    if dry_run:
        log.info("[DRY-RUN] would delete tour %s", tour_id)
        return True

    url = f"{API_V007}/tours/{tour_id}"
    resp = requests.delete(url, headers={"Authorization": auth_header})
    if resp.status_code in (200, 204):
        return True
    log.warning("Failed to delete tour %s: HTTP %s", tour_id, resp.status_code)
    return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    email = os.environ.get("KOMOOT_EMAIL", "").strip()
    password = os.environ.get("KOMOOT_PASSWORD", "").strip()
    user_id_override = os.environ.get("KOMOOT_USER_ID", "").strip()
    dry_run = os.environ.get("DRY_RUN", "false").lower() in ("1", "true", "yes")

    if not email or not password:
        log.error("KOMOOT_EMAIL and KOMOOT_PASSWORD must be set.")
        sys.exit(1)

    if dry_run:
        log.info("DRY-RUN mode — no tours will be deleted.")

    # Step 1: authenticate
    user_id, api_token = login(email, password)
    if user_id_override:
        user_id = user_id_override
        log.info("Using overridden user ID: %s", user_id)

    auth_header = _basic(user_id, api_token)

    # Step 2: list recorded tours
    log.info("Fetching recorded tours for user %s …", user_id)
    tours = list_recorded_tours(user_id, auth_header)

    if not tours:
        log.info("No recorded tours found. Nothing to do.")
        return

    log.info("Found %d recorded tour(s):", len(tours))
    for t in tours:
        log.info("  • %s  —  %s", t["id"], t["name"])

    # Step 3: delete
    ok = 0
    fail = 0
    for t in tours:
        success = delete_tour(t["id"], auth_header, dry_run)
        if success:
            ok += 1
            if not dry_run:
                log.info("Deleted  %s  (%s)", t["id"], t["name"])
        else:
            fail += 1
        time.sleep(DELETE_DELAY)

    log.info(
        "Done. %d deleted, %d failed.%s",
        ok,
        fail,
        " (dry-run)" if dry_run else "",
    )
    if fail:
        sys.exit(1)


if __name__ == "__main__":
    main()
