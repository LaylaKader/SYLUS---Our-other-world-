# SYLUS backend

Private single-owner FastAPI backend for the SYLUS companion. This is an early runnable integration milestone with Docker Compose support, not yet approved for public production hosting.

## Local setup

For a complete local stack, see the repository-root `docker-compose.yml` and `docs/DOCKER_LOCAL_SETUP.md`. Docker Compose keeps PostgreSQL and FastAPI private behind the frontend reverse proxy.

1. Create a private PostgreSQL database.
2. Copy `.env.example` to `.env`. Set `DATABASE_URL`, a long random `SYLUS_OWNER_TOKEN`, a unique `SYLUS_OWNER_PASSWORD`, and a separate random `SESSION_SECRET`. Never reuse the model API key as either secret.
3. For replies, set a model API key in the server-side `.env`. The initial suggested configuration is Groq's OpenAI-compatible endpoint with `openai/gpt-oss-120b`. The free plan has model-specific quotas; check the exact limits in your account. Do not upgrade or add billing unless you explicitly choose to.
4. Install dependencies: `pip install -r requirements.txt`.
5. Start from this directory: `uvicorn app.main:app --reload`. The backend applies numbered migrations automatically at startup.

## API

- `GET /health` — public process health only; contains no private data.
- `GET /v1/time-context` — owner-protected local date/time and last user-message time.
- `GET /v1/messages` — owner-protected full conversation history.
- `POST /v1/messages` — legacy store-only endpoint.
- `POST /v1/chat` — owner-protected user message + Sylus response, using the one configured model provider.
- `GET /v1/memories` — owner-protected active non-archived memories.
- `POST /v1/memories`, `PATCH /v1/memories/{id}`, `DELETE /v1/memories/{id}` — owner-managed memory CRUD.

Every `/v1/*` route requires an owner session cookie or the server-side bootstrap bearer token. The Settings screen signs in with the owner password and receives an HttpOnly, Secure-in-production, SameSite=Lax cookie. The recommended reverse-proxy setup serves frontend and API on one origin. The password is not stored in the browser. CORS is restricted to exact origins and credentials are enabled only for those origins. Never use a wildcard origin for the private app. The built-in in-memory login throttle is a single-process safeguard, not a replacement for host-level rate limiting.

## Provider and privacy notes

The model adapter is OpenAI-compatible and replaceable. The server calls only the configured base URL/model. There is no automatic provider switching, credit purchase, or paid fallback. Provider requests contain the current message, recent chat context, persona instructions, and any retrieved non-sensitive memories. Review the provider's current data policy before using personal conversation content.

Groq's current documentation says inference requests are not retained by default, while temporary logs may be created for reliability or abuse investigations for up to 30 days; exact free-plan limits vary by model and organization. See [Groq data controls](https://console.groq.com/docs/your-data) and [rate limits](https://console.groq.com/docs/rate-limits). Do not treat a free API as equivalent to local/offline processing.

## Current limitations

- Memory retrieval is basic lexical matching, not semantic/vector retrieval.
- Automatic memory extraction is intentionally disabled; owner-created memory CRUD is available, but a reviewable extraction queue is still needed.
- Emotion state is loaded from and saved to the database on each successful reply. Current event detection is intentionally conservative keyword matching; it needs broader evaluation and owner controls.
- Conversation rows are stored with a null conversation_id; multi-thread management is not yet implemented.
- Message pagination, idempotent retry keys, provider timeout/retry policy, structured error telemetry, session revocation/password rotation, and host-level rate limiting remain.
- Image generation/storage, voice, proactive scheduler/push/calls, lore sync, and Android native packaging are not connected.
- Do not expose publicly until host-level rate limiting, database backups/restore, dependency scanning, and production authorization checks are complete.

## Migrations

Apply in numeric order:
- `001_initial.sql` — conversations, messages, memories, knowledge and contact preferences.
- `002_emotion_contact_knowledge.sql` — simulated-emotion and contact/knowledge persistence schema.
- `003_time_and_media.sql` — timezone context, media metadata and activity indexes.

- `004_emotion_dimensions.sql` — adds happiness and disappointment to the persistent emotion state.
- `005_owner_sessions.sql` — registers unique owner sessions and supports server-side logout revocation.

The migration runner records applied filenames in `schema_migrations` and applies unapplied files in numeric order at startup.
