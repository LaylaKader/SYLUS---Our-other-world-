# SYLUS backend

The SYLUS backend is a Python/FastAPI service for the private, single-owner companion application. It handles owner authentication, chat orchestration, persistence, memory and relationship data, media operations, and optional voice and proactive-contact integrations.

This is an actively developed personal application, not a public multi-user API or production SaaS service.

## Responsibilities

- Owner-password sign-in and signed HttpOnly session-cookie authentication.
- Protected private API routes for conversations and owner data.
- AI-provider orchestration and persona/context construction.
- Persistent conversation history in PostgreSQL.
- Saved-memory create, read, update, and delete operations, with memory retrieval for chat context.
- Persisted simulated emotional-state data and relationship/bond progression.
- Sticker catalogue and owner-managed private sticker operations.
- Image uploads, visual-reference collections, and optional image generation/understanding integrations.
- Call records and in-app voice-call support.
- Optional proactive message/call workflows and web-push subscription/delivery endpoints.
- Numbered SQL migrations applied by the backend at startup.

The availability of optional integrations depends on server environment variables, third-party quotas, scheduler setup, and browser/device permissions.

## Local setup

For the complete local stack, use the repository-root docker-compose.yml and docs/DOCKER_LOCAL_SETUP.md.

1. Create a private PostgreSQL database, or use the PostgreSQL service in Docker Compose.
2. Copy the relevant environment example file to .env.
3. Configure a unique database URL, owner password, owner bootstrap token, and independent session secret.
4. Add only the model-provider credentials you intend to use. Optional provider credentials may be left blank.
5. Install dependencies:

   ~~~bash
   pip install -r requirements.txt
   ~~~

6. Start from this directory:

   ~~~bash
   uvicorn app.main:app --reload
   ~~~

The backend applies unapplied numbered migrations during startup. Never use production credentials for local development.

## Authentication and API access

- GET /health is a public process-health endpoint and should not expose private owner data.
- Private /v1/* routes require a valid owner session cookie or the server-side bootstrap bearer token.
- The owner signs in through POST /v1/session; sign-out revokes the session through DELETE /v1/session.
- The recommended deployment serves the frontend and API on one origin through a reverse proxy.
- CORS should be restricted to exact trusted origins. Do not use wildcard origins with credentialed requests.
- Private API responses are marked not to be cached.

The current design authenticates one owner. It is not multi-tenant: do not add public registration or additional testers by simply sharing the owner password. A future multi-user release requires tenant-aware authorization on every query and mutation, isolated media access, account lifecycle controls, and automated cross-account security tests.

## Configuration and providers

Provider credentials are read from the backend environment. The application supports configured AI provider integrations, with the exact provider pool and model determined by the current backend configuration. Optional services include Cloudflare Workers AI for image-related capabilities, ElevenLabs for generated speech, and web-push/background scheduling for proactive contact.

Do not assume that an integration is active because its UI is present. Check the relevant readiness endpoint and server configuration. Never hard-code secrets or return them to the frontend.

Requests sent to model, speech, image, or search providers may contain conversation text, prompts, or media needed for the requested operation. Review each provider's privacy, retention, and acceptable-use terms before using sensitive information.

## Data and privacy

PostgreSQL stores application records such as messages, memories, emotion/bond state, call information, and metadata for private media and visual references. Private endpoints are protected by owner authentication. Uploaded files and provider requests may be handled by services outside the database; database privacy alone does not mean all processing is local.

Do not log or commit:
- Owner passwords, bootstrap tokens, session secrets, or session cookies.
- Database URLs or third-party API keys.
- Private conversation exports, personal memories, or private uploaded images.
- Production environment files or database backups.

## Migrations

The backend applies numbered SQL migration files in order and records completed migrations in schema_migrations. Review each migration before applying it to a production database. Back up important data before schema changes. Never run destructive migrations or reset production data as a debugging shortcut.

## Known limitations

- Model output can hallucinate, contradict prior context, or fail when a provider is unavailable or rate-limited.
- Memory retrieval can miss or mis-rank relevant information; it should not be treated as a perfect long-term memory system.
- Provider behaviour, model names, free-tier limits, and API compatibility can change.
- Voice, image generation/understanding, push delivery, and proactive contact depend on external configuration and permissions.
- The application has not undergone an independent security audit and has no formal uptime guarantee.
- Multi-user accounts, tenant isolation, public onboarding, and a safe public demo/tester mode are not implemented.

## Copyright and permission

Copyright © 2026 Layla Kader Suma. All rights reserved. This backend is part of a source-available, proprietary project and is not distributed under an open-source licence. Do not copy, adapt, redistribute, repackage, commercialise, or use this backend as the foundation of another project without the copyright owner's prior written permission. Third-party packages and services remain subject to their own licences and terms.
