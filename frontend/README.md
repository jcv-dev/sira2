# SIRA panel académico — frontend

React UI for the read-only SIRA API in [`../backend`](../backend). Built to be fast, legible and personal where the original registry UI is not.

## Stack

- **React 19 + Vite + TypeScript**
- **Tailwind CSS 4** with a custom theme (see "Design" below)
- **shadcn/ui** components (new-york style, `radix-ui`, `cn`)
- **lucide-react** icons
- **TanStack Query** for data fetching, caching and refresh
- **Sonner** toasts

## Run

```bash
npm install
npm run dev        # http://localhost:5173 (proxies /api → 127.0.0.1:8000)
```

The backend must be running (`cd ../backend && uv run uvicorn app.main:app --port 8000`).

| Script | |
|---|---|
| `npm run dev` | dev server with API proxy |
| `npm run build` | type-check + production build to `dist/` |
| `npm run preview` | serve the production build |
| `npm run lint` | oxlint |

## Configuration

| Variable | Default | Notes |
|---|---|---|
| `VITE_API_URL` | `/api` | Base URL of the SIRA API. Dev uses the Vite proxy; for deployments set this to the API origin (and set `SIRA_CORS_ORIGINS` in the backend). |

Copy `.env.example` to `.env` to override.

## Structure

```
src/
├── lib/
│   ├── api.ts        # typed client + response models
│   ├── format.ts     # Intl formatters, grade bands, period labels
│   ├── router.ts     # tiny hash router (deep-linkable state, zero deps)
│   └── theme.tsx     # light/dark/system theme provider
├── hooks/
│   ├── use-sira.ts   # TanStack Query hooks per endpoint
│   └── refresh.tsx   # manual refresh: busts cache server-side (?refresh=true)
├── components/
│   ├── ui/           # shadcn components
│   ├── app-shell.tsx # rail + mobile header + skip link
│   ├── period-spine.tsx  # the semester spine (hero element)
│   ├── grade-chip.tsx    # grade scale as colour
│   └── course-table.tsx / course-list.tsx / estado-badge.tsx …
└── pages/            # Resumen, Calificaciones, Matrícula, Programa, Equivalencias, Contacto
```

## Design notes

- **Colour is data.** The 0.0–5.0 grade scale drives the chip palette: solid green ≥ 4.5, soft green ≥ 4.0, outlined ≥ 3.0, red below. Carmine is the only identity/interactive colour (Univalle red), mustard marks the current period.
- **One memorable element.** The period spine on the dashboard: your semesters on a single line, per-period averages, ending in the accumulated average. It draws itself once on load and respects `prefers-reduced-motion`.
- **Tables over cards.** Data lives in tables and hairline-separated rows; boxes are reserved for the few places that need grouping.
- **Locale-correct.** All numbers and dates go through `Intl` (`es-CO`), tabular numerals everywhere.
- **URL is state.** Sections, the selected period (`#/calificaciones?periodo=…`) and the program search (`#/programa?q=…`) are deep-linkable.
