# SYLUS frontend

Responsive React/Vite interface for the private, single-owner SYLUS companion.

## Run the visual preview
```bash
npm install
npm run dev
```
Open the local Vite URL. The initial screen is an offline design preview; it does not pretend an AI conversation is live.

## Connect a private API
Set `VITE_API_BASE_URL` to the HTTPS base URL of the private app, or enter the app address in Settings. Sign in with the owner password configured on the private server. The server returns a signed HttpOnly session cookie; the password is not stored in browser storage. For the recommended Docker Compose setup, frontend and API share one origin through Nginx.

The model provider key is configured only on the backend server in `MODEL_API_KEY`. Never put it in this frontend or in GitHub. If the provider key is absent, the interface reports that chat setup is incomplete and does not send messages to a paid fallback.

## Current integration boundary
The UI reads persisted message history, saves and renders user/assistant turns, reads and manages memories, and displays Dhaka time context. Automatic memory extraction is intentionally disabled; the owner can add, edit, and delete memories manually. Image generation, voice, proactive contact, and Android native packaging are not connected yet.

Do not expose this frontend as a public app until the backend has owner-only provisioning, HTTPS, rate limiting, database backups, restore tests, and production authorization checks. See the repository root `README.md` and `docs/DOCKER_LOCAL_SETUP.md`.
