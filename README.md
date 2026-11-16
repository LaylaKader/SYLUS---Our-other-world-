# SYLUS — A world of our own

Private, single-owner companion app project.

## Current source layout
- `frontend/` — responsive React/Vite PWA interface.
- `backend/` — FastAPI owner-session API, chat provider adapter, persistent emotion state, and migrations.
- `character/` — versioned persona and canon reference notes.
- `docs/` — implementation, security, and hosting notes.

## Run with Docker Compose
1. Copy `.env.compose.example` to `.env`.
2. Replace every placeholder with private values. Generate independent random values for `SYLUS_OWNER_TOKEN`, `SYLUS_OWNER_PASSWORD`, and `SESSION_SECRET`.
3. Set `MODEL_API_KEY` only if you choose to use the configured external provider. The sample uses Groq's free-plan endpoint/model and has no paid fallback.
4. Run `docker compose up --build`.
5. Open `http://localhost:8080`. Sign in under Settings using the owner password.

PostgreSQL is internal to the Compose network and has a persistent named volume. The API is not directly published; Nginx serves the frontend and proxies `/v1/*` to FastAPI on the private network. The backend applies idempotent SQL migrations at startup.

## Hosted preview
A Render Blueprint and single-container Dockerfile are included. See `docs/RENDER_PREVIEW.md` before applying it. The preview uses Neon Postgres rather than Render Free Postgres because Render's free database expires after 30 days. Do not apply the Blueprint until you have reviewed its resources and are comfortable with the free-tier limitations.

## Run without Docker
See `frontend/README.md` and `backend/README.md`.

## Important
This is still an early private beta. Before public hosting, set `APP_ENV=production`, use HTTPS, configure the exact public origin, use a persistent private database, set strong secrets in the host's secret manager, and complete backup/restore and authorization checks. Never commit `.env`, API keys, chat exports, private images, or personal memory records. The GitHub repository is public, so only source code and placeholder configuration belong here.

The UI is not a completed native Android app. It has a PWA manifest and service worker; Android push notifications, proactive calls, voice, image generation, Together, and the 3D avatar are later modules.
