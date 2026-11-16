# SYLUS backend (foundation)

This is the first independently coded backend foundation. It is not yet a complete chat agent or a deployed service.

## Run locally

1. Create a PostgreSQL database.
2. Copy `.env.example` to `.env` and set `DATABASE_URL` and a long random `SYLUS_OWNER_TOKEN`.
3. Install dependencies: `pip install -r requirements.txt`.
4. Apply `migrations/001_initial.sql` to the database.
5. Start: `uvicorn app.main:app --reload` from this directory.
6. `GET /health` is public and returns service status. All `/v1/*` routes require `Authorization: Bearer <SYLUS_OWNER_TOKEN>`.

## Current API

- `GET /v1/messages` reads persisted messages.
- `POST /v1/messages` stores a user message.
- `GET /v1/memories` lists active memories.

## Not implemented yet

The response-generation/model adapter, automatic memory extraction and retrieval, message pagination, owner-token provisioning UI, voice provider, background scheduler, Android shell, and production deployment are still pending. Do not expose this API publicly until HTTPS, secrets, database access controls, rate limits, backups, and owner-only authorization have been reviewed.
