# SIRA API

A small **read-only** FastAPI service that wraps [SIRA (Universidad del Valle's academic registry)](https://sira1.univalle.edu.co/sra/) and exposes your student data as clean JSON, so you can build your own UI instead of using the legacy web app.

> **Solo lectura.** The API never submits actions that modify anything in SIRA. It only performs the same queries the web UI does when *viewing* your grades, enrollment, contact info, etc. Use it responsibly and politely (it caches responses to avoid load on the production server).

## Features

- Login with your own SIRA credentials (session handled server-side).
- Clean, typed JSON for:
  - student profile & program (`/me`)
  - contact information (`/me/contact`)
  - full academic record: periods, courses, grades, averages (`/grades`)
  - single periods (`/grades/periods/{code}`)
  - current enrollment ("tabulado") (`/enrollment`)
  - program prerequisites (`/program`)
  - equivalences (`/equivalences`)
- TTL response cache (default 5 min, `?refresh=true` to bypass).
- Automatic re-login: SIRA allows one session per user, so it self-heals when you open the web UI in a browser.
- Optional bearer-token protection for the API itself.

## Setup

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
cp .env.example .env
# edit .env with your credentials
uv sync
```

`.env`:

```env
SIRA_BASE_URL=https://sira1.univalle.edu.co/sra
SIRA_USERNAME=your-code-here
SIRA_PASSWORD=your-password
SIRA_CACHE_TTL_SECONDS=300
SIRA_TIMEOUT_SECONDS=30
# SIRA_API_TOKEN=change-me   # uncomment to require Authorization: Bearer <token>
```

> `.env` is gitignored — keep it that way. Credentials are never written to disk by the app itself.

## Run

```bash
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

- Interactive docs: <http://127.0.0.1:8000/docs>
- Health check: `GET /healthz`

Credentials can also be provided at runtime instead of `.env`:

```bash
curl -X POST http://127.0.0.1:8000/session/login \
  -H 'Content-Type: application/json' \
  -d '{"username": "2259459-3743", "password": "..."}'
```

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/session` | Current session state (does not log in by itself) |
| POST | `/session/login` | Explicit login (optional body overrides credentials) |
| POST | `/session/logout` | Close the SIRA session |
| GET | `/me` | Student identity, program, available academic folders |
| GET | `/me/contact` | Contact / personal info form data |
| GET | `/program` | Program, resolution, periods, prerequisite list |
| GET | `/grades` | Full academic record (all periods, courses, averages) |
| GET | `/grades/periods` | Period index (no course lists) |
| GET | `/grades/periods/{codigo}` | One period, e.g. `202408041` (targeted query) |
| GET | `/enrollment` | Current enrollment report ("tabulado") |
| GET | `/equivalences` | Equivalences registered in the academic record |

All data endpoints accept `?refresh=true` to bypass the cache. `/me`, `/program`, `/grades` and `/grades/periods` accept `?carpeta=3743|00|DIU|698` to pick another academic folder (see `/me` for the available ones).

### Examples

```bash
# Average + periods
curl -s localhost:8000/grades | jq '.promedio_total, [.periodos[].nombre]'

# Courses still in progress this term
curl -s localhost:8000/grades | jq '[.periodos[-1].cursos[] | select(.estado == "EN_CURSO") | {codigo, nombre}]'

# Current enrollment
curl -s localhost:8000/enrollment | jq '[.cursos[] | {codigo, nombre, creditos, estado}]'
```

## Fields worth knowing

- `estado`: derived best-effort — `APROBADA`, `REPROBADA`, `EN_CURSO`, or `CANCELADA` (with `fecha_cancelacion`). Non-numeric grades (e.g. `E.X`, `A.P` homologation codes) are kept in `nota_raw` with `estado: null`.
- `tipologia` / `funcionalidad` / `componente`: raw SIRA columns (`TM`, `FUN`, `COM`) — the API does not guess their meaning.
- `otros`: extra summary cells found in the period box (cumulative credits, % approved, etc.).

## Development

```bash
uv run pytest        # 22 offline tests, no network needed
```

Tests use sanitized fixtures of the real pages in `tests/fixtures/` (all personal data replaced). The client tests use `httpx.MockTransport`, so they never touch SIRA.

## Architecture

```
app/
├── main.py      # FastAPI routes, error mapping, optional bearer token
├── client.py    # httpx session, login, request serialization, TTL cache, auto-relogin
├── parsers.py   # pure HTML -> pydantic parsers (the interesting part)
├── models.py    # response models
└── config.py    # settings from environment / .env
```

### How the scraping works

1. `POST /sra/` with `usu_login_aut` / `usu_password_aut` → `PHPSESSID` cookie.
2. `accion=Consultar Historial` → profile + available "carpetas" + `hia_*` form fields.
3. `accion=Consultar Estudiante` → academic periods (`202408041`, ...).
4. `accion=Generar Carpeta` → full record; a single period can be fetched with its `DetalleCarpeta` value.
5. `accion=Generar Tabulado` → current enrollment.
6. `desplegarFmInformacionDeContacto` → contact form values.
7. `accion=ListadoPrerrequisitos` → prerequisite list.

The legacy HTML is malformed in creative ways (stray `<td>`s, nested summary tables, duplicate `selected` options, form fields bleeding into text). The parsers in `app/parsers.py` handle these quirks and have regression tests for each one found so far.

## Caveats

- **Personal use.** Respect Universidad del Valle's terms of service; this is an unofficial, read-only client for your own account.
- SIRA kills all other sessions when a new login happens, so using the API logs your browser session out (and vice versa — the API recovers automatically).
- Response shape depends on the current SIRA HTML; if SIRA changes its markup, update `app/parsers.py` (and add a fixture).
