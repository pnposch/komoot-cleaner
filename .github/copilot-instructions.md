# Copilot Instructions

## Project overview

Single-file Python tool (`cleaner.py`) that bulk-deletes **recorded** (past/completed) tours from a Komoot account via Komoot's undocumented REST API. Deployed via Docker Compose and run manually.

## Running the tool

```bash
# Build
docker compose build

# Dry-run (lists tours, no deletions)
DRY_RUN=true docker compose run --rm komoot-cleaner

# Live run
docker compose run --rm komoot-cleaner

# Without Docker
pip install -r requirements.txt
KOMOOT_EMAIL=x KOMOOT_PASSWORD=y python cleaner.py
```

## Architecture

Everything lives in `cleaner.py` — three logical layers called in sequence from `main()`:

1. **`login(email, password)`** — `GET api.komoot.de/v006/account/email/{email}` with HTTP Basic Auth (email:password). Returns `(user_id, api_token)`. All subsequent calls use Basic Auth with `(user_id, api_token)`.
2. **`list_recorded_tours(user_id, auth_header)`** — `GET /v007/users/{userId}/tours/?type=recorded` with HAL+JSON pagination via `_links.next`. Each tour is validated: `type == "recorded_route"` or it is skipped with a warning.
3. **`delete_tour(tour_id, auth_header, dry_run)`** — `DELETE /v007/tours/{tourId}`, 150 ms delay between calls.

## Key conventions

- **Two-layer safety guard** — planned routes must never be deleted. Layer 1: `?type=recorded` query param (server-side). Layer 2: per-tour `type == "recorded_route"` assertion before any tour is queued for deletion. Both layers must remain in place if the listing logic is changed.
- **Auth flow** — v006 for login, v007 for all data operations. Do not mix them.
- **`DRY_RUN` env var** — checked in `main()`, threaded through to `delete_tour()`. The listing always runs; only the DELETE is skipped.
- **`KOMOOT_USER_ID`** — optional override; auto-detected from the login response if omitted.
- **No external deps beyond `requests`** — keep it that way unless there is a strong reason.
- **HTTP 401 and 403 both mean bad credentials** on the Komoot auth endpoint.
