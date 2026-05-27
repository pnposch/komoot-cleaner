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

1. **`login(email, password)`** — `GET api.komoot.de/v006/account/email/{email}/` (raw email, trailing slash) with HTTP Basic Auth (email:password). Returns `(user_id, api_token)`. All subsequent calls use Basic Auth with `(user_id, api_token)`.
2. **`list_recorded_tours(user_id, auth_header)`** — `GET /v007/users/{userId}/tours/` (no query params) with HAL+JSON pagination via `_links.next`. Each tour is validated: `type == "tour_recorded"` or it is silently skipped. Planned tours have type `"tour_planned"`.
3. **`delete_tour(tour_id, auth_header, dry_run)`** — `DELETE /v007/tours/{tourId}`, 150 ms delay between calls.

## Key conventions

- **Safety guard** — planned routes must never be deleted. Per-tour `type == "tour_recorded"` assertion filters out all non-recorded tours before any tour is queued for deletion. (`"tour_planned"` = planned routes, `"tour_recorded"` = completed rides.) This check must remain in place if listing logic changes.
- **Auth flow** — v006 for login, v007 for all data operations. Do not mix them.
- **`DRY_RUN` env var** — checked in `main()`, threaded through to `delete_tour()`. The listing always runs; only the DELETE is skipped.
- **`KOMOOT_USER_ID`** — optional override; auto-detected from the login response if omitted.
- **No external deps beyond `requests`** — keep it that way unless there is a strong reason.
- **HTTP 401 and 403 both mean bad credentials** on the Komoot auth endpoint. HTTP 404 means the account email was not found.
