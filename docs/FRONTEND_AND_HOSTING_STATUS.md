# SYLUS frontend and hosting status

## UI direction
The interface uses a near-black/charcoal base, muted ruby and burgundy, violet/lavender, champagne-gold details, subtle stars, and restrained crow/rose-inspired ornament. It uses a serif display face with a clean sans-serif UI font. The layout is responsive, with a mobile slide-out navigation and separate Chat, Bond, Memories, Gallery, and Settings views. Decorative details stay behind the conversation area.

## Implemented in source
- React + Vite responsive PWA shell with manifest and SVG app icon.
- Offline visual preview does not fabricate a chat transcript.
- Private owner sign-in uses a server-signed HttpOnly session cookie; password is not stored in browser storage.
- Private API session, message history, and memory endpoints are connected in the UI.
- Chat UI calls `POST /v1/chat` and renders both returned message bubbles.
- Memory controls allow the owner to create, edit, and permanently delete memories.
- Dhaka-local time context is supplied to the agent.
- Artificial emotion state is loaded and saved in PostgreSQL; initial event detection is conservative and keyword-based.
- Database migrations run automatically at backend startup and are tracked in `schema_migrations`.
- Docker Compose runs frontend, private API, and PostgreSQL. Only the Nginx frontend port is published; API and database stay on the private Compose network.
- GitHub Actions checks frontend build, backend tests, Docker Compose configuration, and container builds.

## Not implemented yet
- Automatic memory extraction (intentionally disabled until a more complete review workflow exists).
- Semantic/vector memory retrieval; current retrieval is lexical and basic.
- Knowledge importer, scheduled official game update monitoring, and source-aware lore retrieval.
- Image generation provider, private object storage, and image message attachments.
- Voice input/output, spontaneous message scheduler, push notifications, and proactive calls.
- Android native shell; current PWA is installable-capable, not a signed native APK.
- Together/screen sharing and 3D avatar renderer.

## Hosting gate
The repository now has a repeatable Docker Compose path, but I will call it host-ready only after the Docker CI job passes and the private deployment is configured. Before internet hosting:
1. Use a private VPS or managed container host with HTTPS and persistent storage.
2. Set strong independent secrets in the host secret manager; never commit the real `.env`.
3. Use a persistent private PostgreSQL volume/database and test backup restoration.
4. Configure the model provider key server-side. Review the provider's retention policy; no paid fallback is enabled.
5. Set `APP_ENV=production`, the exact allowed origin, and the HTTPS domain.
6. Add host-level rate limiting and verify login/session behavior through the reverse proxy.
7. Test owner-only access, history persistence, memory CRUD, model failure recovery, and Android PWA installation.
8. Do not expose the database or backend port directly to the public internet.

The PWA manifest is not equivalent to a native Android app. Background calls, proactive contact, voice, and image generation require further native/backend work.
