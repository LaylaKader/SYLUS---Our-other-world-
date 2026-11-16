# SYLUS frontend

Responsive React/Vite interface for the private, single-owner SYLUS companion.

## Run the visual preview
```bash
npm install
npm run dev
```
Open the local Vite URL. The initial screen is an offline design preview; it does not pretend an AI conversation is live.

## Connect a private API
Set `VITE_API_BASE_URL` to the HTTPS base URL of the private backend, or enter it in Settings. Enter the owner bearer token in Settings. The token is held in sessionStorage for the current browser session only; it is not committed or written into the build.

## Current integration boundary
The UI currently reads persisted message history, saves user messages, reads memories, and displays server time context. The existing backend does not yet generate Sylus replies, so sending currently saves the message and clearly reports that reply generation is not connected. Image generation, voice, proactive contact, and Android packaging are not connected yet.

Do not deploy this frontend as a public app until the backend has owner-only provisioning, rate limiting, HTTPS, secure session handling, and the database is provisioned. The current bearer-token mechanism is a development bridge, not the final production login design.
