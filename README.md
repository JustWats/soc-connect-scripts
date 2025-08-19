# Security Onion Case Puller

Pulls **Security Onion** case bundles via the Security Onion Connect REST API with using a **client credentials** OAuth2 flow, then writes tidy JSON files per case (case, comments, events, history, artifacts). It’s a single-file Python script with minimal dependencies and no external CLI framework.

---

## Features

* **Simple OAuth2**: `client_credentials` using `client_secret_basic` (HTTP Basic auth to `/oauth2/token`).
* **Case discovery**: Queries `/connect/events` for `so_kind:case`, parses UUIDs from instances.
* **Bundle fetch**: Pulls `case`, `comments`, `events`, `history`, `artifacts` using primary + alternate endpoints.
* **Resilient outputs**:

  * Writes valid JSON for success.
  * Writes `.err.<status>.txt` when non-JSON or error.
  * Treats some empty/quirky responses (e.g., history/artifacts 200/404/500) as empty lists to keep output JSON-friendly.

---

## Requirements

* Python **3.9+**
* [`requests`](https://pypi.org/project/requests/) (usually preinstalled on many distros)

If needed, install into a virtualenv:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install requests
```

---

## Quick Start

1. Open the script and **edit the Config** block near the top:

   ```python
   BASE_URL = "https://<your-so-host>"
   CLIENT_ID = "your_oauth_client"
   CLIENT_SECRET = "your_oauth_secret"
   VERIFY_SSL = False  # set True if you trust the CA
   OUT_DIR = pathlib.Path("./cases")
   EVENT_LIMIT = 5000
   TIMEOUT = 45
   ```
2. Run it:

   ```bash
   python3 pull-soc-cases.py
   ```
3. Outputs are written under `./cases/<case-id>/`.

Example console output (colors may vary depending on terminal):

```
 Security Onion Case Puller
────────────────────────────────────────────────────────────
Base URL : https://<your-so-host>
Output   : /path/to/cases
────────────────────────────────────────────────────────────
[*] Requesting OAuth2 token…
[*] Discovering cases…
[+] Found X cases (wide window)
[•] [ #/X ] 03320432  case ✓  art ✓  com ✓  evt ✓  hist ✓  Case Title
…
────────────────────────────────────────────────────────────
✓  Bundles OK : #/X
i  Saved to  : /path/to/cases
```

---

## What gets saved

For each case ID a folder is created:

```
cases/
  <case-id>/
    case.json
    comments.json
    events.json
    history.json            # may be [] if API returns 200 with no body
    artifacts.json          # may be [] if API returns 404/500
    comments.err.<code>.txt # only when non-JSON/error
    … etc
```

This keeps the output usable in pipelines even when the upstream API returns HTML or an error page.

---

## How it works (high level)

1. **Get OAuth2 token**

   * `POST /oauth2/token` with form `grant_type=client_credentials` and HTTP Basic auth (client id/secret).
   * On success, sets `Authorization: Bearer <token>` on the session for subsequent requests.

2. **Discover case IDs**

   * `GET /connect/events` with query params:

     * `query=so_kind:case`
     * `range=2000/01/01 00:00:00 - 2030/01/01 00:00:00`
     * `eventLimit=<EVENT_LIMIT>`
   * Walks `events[].payload` (and top-level) for keys `so_case_id | caseId | id`; accepts values that parse as UUIDs.

3. **Fetch bundle per case**

   * For each of: `case`, `comments`, `events`, `history`, `artifacts`, it tries a **primary** then an **alternate** path, e.g.:

     * `case`: `/connect/case/{id}`
     * `comments`: `/connect/case/{id}/comments` or `/connect/case/comments/{id}`
     * `events`: `/connect/case/{id}/events` or `/connect/case/events/{id}`
     * `history`: `/connect/case/{id}/history` or `/connect/case/history/{id}`
     * `artifacts`: `/connect/case/{id}/artifacts` or `/connect/case/artifacts/{id}`
   * If body is JSON: saves `*.json`.
   * If body is empty but 200: saves an **empty JSON list** for a stable output shape.
   * If non-JSON or error: writes `.err.<status>.txt` with the raw body for inspection.

---

## TLS & certificates

* The script disables TLS verification by default (`VERIFY_SSL=False`) to make it work against self-signed deployments.
* For production: set `VERIFY_SSL=True` and provide a CA bundle via `REQUESTS_CA_BUNDLE` or install your CA.

---

## Security

* Don’t commit real client IDs/secrets. Use environment variables, a `.env` file, or a secrets manager in your fork.
  * Just scrape the first two config lines, and run this prior to your first run of the script:
```
export BASE_URL = "https://<your-so-host>"
export CLIENT_ID = "your_oauth_client"
export CLIENT_SECRET = "your_oauth_secret"
export VERIFY_SSL = False
export OUT_DIR = pathlib.Path("./cases")
export EVENT_LIMIT = 5000
export TIMEOUT = 45
```
* Consider read-only scopes for the OAuth2 client permissions.

---

## License

GNU General Public License v3.0
