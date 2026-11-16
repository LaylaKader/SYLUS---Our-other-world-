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


## Database migrations

Apply migrations in numeric order:

- `migrations/001_initial.sql` — conversations, messages, memories, initial knowledge, and contact preferences.
- `migrations/002_emotion_contact_knowledge.sql` — persistent simulated-emotion state/events, explicit channel restrictions, queued outbound sequences with up to three ordered bubbles, source registry, and source-aware lore records.

Migration 002 defines storage only. Emotion transitions, scheduled message generation/delivery, call initiation, live web retrieval, and scheduled official-source synchronization still require application services and end-to-end tests. Do not interpret the presence of these tables as proof those behaviours are live.


- `migrations/003_time_and_media.sql` — owner timezone, private media attachment metadata, and message activity indexes.
- `GET /v1/time-context` — owner-protected current local date/time, weekday, timezone, last user-message timestamp, and elapsed time since that message. Uses Asia/Dhaka by default and database UTC timestamps.

## Image generation status

`app/media.py` defines replaceable image-generation and private-storage interfaces. The provider, private object storage, chat attachment endpoint, and client image rendering are not connected yet. See `../docs/IMAGE_GENERATION.md`. Do not put image-provider credentials in the client or public repository.
