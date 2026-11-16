# SYLUS frontend and hosting status

## UI direction
The interface uses a near-black/charcoal base, muted ruby and burgundy, violet/lavender, champagne-gold details, subtle stars, and restrained crow/rose-inspired ornament. It uses a serif display face with a clean sans-serif UI font. The layout is responsive, with a mobile slide-out navigation and separate Chat, Bond, Memories, Gallery, and Settings views. Decorative details stay behind the conversation area.

## Frontend milestone
- React + Vite application created under `frontend/`.
- Offline visual preview does not fabricate a chat transcript.
- Private owner connection form is in Settings.
- Connected mode reads history, memories, and Dhaka time from the API.
- Chat UI calls `POST /v1/chat` and renders the user/assistant messages returned by the backend.
- PWA manifest and SVG app icon added for future Android home-screen installation.

## Hosting gate
The project is not yet host-ready. Before hosting the private app:
1. Run CI and fix all build/test failures.
2. Provision a private PostgreSQL database and apply all three migrations.
3. Set server-side owner token and model API key in the host's secret manager.
4. Confirm provider data policy and free quota; do not enable paid fallback.
5. Set exact HTTPS CORS origin.
6. Add secure owner session provisioning instead of a static bearer token in the browser.
7. Add rate limiting, TLS, backups, restore verification, and logs that exclude message bodies and secrets.
8. Test owner-only access, history persistence, failed model requests, and browser restart behavior.
9. Verify PWA install and later Capacitor/Android packaging on a real Android device.

The PWA manifest is not equivalent to a native Android app. Background calls, push notifications, voice, and autonomous scheduling require further native/backend work.
