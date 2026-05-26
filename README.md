# komoot-cleaner

Deletes all **recorded** (past/completed) routes from a Komoot account.  
Planned routes are never touched (two-layer protection — see below).

## How it works

1. Authenticates via Komoot's undocumented REST API using HTTP Basic Auth.
2. Fetches every recorded tour with `GET /v007/users/{userId}/tours/?type=recorded` (paginated).
3. Guards each result: skips anything whose `type` field is not `"recorded_route"`.
4. Deletes each tour with `DELETE /v007/tours/{tourId}`.

### Protection against deleting planned routes

| Layer | Mechanism |
|---|---|
| **Server-side** | `?type=recorded` query param — Komoot only returns recorded tours |
| **Client-side** | Per-tour `type == "recorded_route"` assertion — skips and warns on anything unexpected |

## Quick start

```bash
cp .env.example .env
# Edit .env with your credentials
docker compose run --rm komoot-cleaner
```

## Configuration (`.env`)

| Variable | Required | Default | Description |
|---|---|---|---|
| `KOMOOT_EMAIL` | ✅ | — | Komoot login email |
| `KOMOOT_PASSWORD` | ✅ | — | Komoot password |
| `KOMOOT_USER_ID` | ❌ | auto-detected | Override numeric user ID |
| `DRY_RUN` | ❌ | `false` | List tours without deleting |

## Dry-run first (recommended)

```bash
DRY_RUN=true docker compose run --rm komoot-cleaner
```

Prints every recorded tour that *would* be deleted, without touching anything.

## Building manually

```bash
docker compose build
docker compose run --rm komoot-cleaner
```

## Quick one-off: browser console snippet

If you just want a **one-time manual cleanup** while already logged in at komoot.com, no setup is needed. This approach was [originally shared by RingoRohe](https://gist.github.com/RingoRohe/e15709c199cd388435567fadafa913a2).

1. Go to `https://www.komoot.com/de-de/user/<your-id>/activities?type=recorded`
2. Open the browser DevTools console (F12)
3. Paste and run:

```js
let func = () => {
  let tour = document.querySelector('li[data-tour-id] [data-test-id="t_actions_delete"]');
  if (tour) {
    tour.click();
    window.setTimeout(() => {
      document.querySelector('button[data-test-id=t_actions_delete_confirm]').click();
      window.setTimeout(() => { func(); }, 300);
    }, 300);
  }
};
func();
```

> **Note:** This deletes whatever tours are currently listed on the page. There is no dry-run or type-guard — ensure you are on the `?type=recorded` filtered URL.

---

## Running without Docker

```bash
pip install -r requirements.txt
export KOMOOT_EMAIL=your@email.com
export KOMOOT_PASSWORD=yourpassword
export DRY_RUN=true   # optional
python cleaner.py
```
