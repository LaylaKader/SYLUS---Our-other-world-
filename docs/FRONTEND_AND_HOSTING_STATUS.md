# SYLUS frontend and hosting status

## UI direction
The interface uses a near-black/charcoal base, muted ruby and burgundy, violet/lavender, champagne-gold details, subtle stars, and restrained crow/rose-inspired ornament. It uses a serif display face with a clean sans-serif UI font. The layout is responsive, with a mobile slide-out navigation and separate Chat, Bond, Memories, Gallery, and Settings views. Decorative details stay behind the conversation area.

## Implemented in source
- React + Vite responsive PWA shell with manifest, SVG app icon, and a service worker that caches only the app shell/static assets; private API responses are never cached.
- Offline visual preview does not fabricate a chat transcript.
- Private owner sign-in uses a server-signed HttpOnly session cookie; password is not stored in browser storage.
- Private API session, message history, and memory endpoints are connected in the UI.
- Chat UI calls `POST /v1/chat` and renders both returned message bubbles.
- Memory controls allow the owner to create, edit, and permanently delete memories; the owner can mark a memory sensitive so it is stored but excluded from automatic retrieval.
- Dhaka-local time context is supplied to the agent.
- Memory retrieval filters conversational filler, ranks matching terms, supports Unicode words, and treats saved memory text as untrusted data rather than instructions.
- Artificial emotion state is loaded and saved in PostgreSQL; initial event detection is conservative and keyword-based.
- Owner sessions use unique signed tokens registered server-side; logout revokes the session record.
- Database migrations run automatically at backend startup and are tracked in `schema_migrations`.
- Docker Compose runs frontend, private API, and PostgreSQL. Only the Nginx frontend port is published; API and database stay on the private Compose network. Nginx applies separate rate limits to owner login, chat, and general API routes.
- GitHub Actions checks frontend build, backend tests, Docker Compose configuration, container builds, migrations, owner login/logout, protected API access, and memory CRUD.

## Not implemented yet
- Automatic memory extraction with an owner review/approval queue (intentionally disabled until that workflow exists).
- Semantic/vector memory retrieval; current retrieval is lexical and basic.
- Knowledge importer, scheduled official game update monitoring, and source-aware lore retrieval.
- Image generation provider, private object storage, and image message attachments.
- Voice input/output, spontaneous message scheduler, push notifications, and proactive calls.
- Android native shell; current PWA is installable-capable, not a signed native APK.
- Together/screen sharing and 3D avatar renderer.

## Hosting gate
The repository has a repeatable Docker Compose path and the current full CI run has passed. A private internet-hosted preview still requires deployment credentials, HTTPS, persistent storage, and a configured model key; it is not deployed yet. Before internet hosting:
1. Use a private VPS or managed container host with HTTPS and persistent storage.
2. Set strong independent secrets in the host secret manager; never commit the real `.env`.
3. Use a persistent private PostgreSQL volume/database and test backup restoration.
4. Configure the model provider key server-side. Review the provider's retention policy; no paid fallback is enabled.
5. Set `APP_ENV=production`, the exact allowed origin, and the HTTPS domain.
6. Retain the included Nginx rate limits and add host-level edge protection; verify login, server-side logout revocation, and session expiry through the reverse proxy.
7. Test owner-only access, history persistence, memory CRUD, model failure recovery, and Android PWA installation.
8. Do not expose the database or backend port directly to the public internet.

The PWA manifest is not equivalent to a native Android app. Background calls, proactive contact, voice, and image generation require further native/backend work.
