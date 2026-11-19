# SYLUS frontend

The SYLUS frontend is a responsive React/Vite web application and installable Progressive Web App (PWA). It provides the conversation interface and owner-facing personal areas for the private, single-owner SYLUS companion.

## User-facing areas

- Conversation history, multi-bubble replies, message editing, selection, and copy.
- Bond and relationship overview.
- Saved-memory management.
- Call history and in-app voice-call interface.
- Gallery and visual-reference collections.
- Sticker picker, private sticker collection, and Sticker Studio.
- Settings for private server connection, owner sign-in, notifications, proactive contact, and media/voice configuration.

Some controls depend on backend routes and server-side provider configuration. A visible interface does not necessarily mean the corresponding external provider is configured or available.

## Local frontend preview

~~~bash
npm install
npm run dev
~~~

Open the local Vite URL. Without a configured private backend, the frontend runs in preview mode; it does not provide a separate public account or live AI service.

## Connect to the private backend

Set VITE_API_BASE_URL to the HTTPS base URL of your private SYLUS backend, or enter the private API address in Settings. Sign in with the owner password configured on that server.

The backend issues a signed HttpOnly session cookie. The password is not stored in browser local storage. In the recommended Docker Compose setup, Nginx serves the frontend and proxies the API on the same origin.

AI-provider credentials, database credentials, owner bootstrap tokens, and session secrets must remain in the backend environment. **Never put secrets in Vite variables or frontend source code**: Vite variables prefixed with VITE_ are exposed to the browser.

## PWA and installation

The frontend includes a web app manifest, application icons, and a production service-worker registration. A supported browser may offer an install or “Add to Home Screen” action. Installation does not create a new account or bypass owner authentication; the same private sign-in is required.

The app's public-facing description is:

> A private AI companion with persistent conversations, character-driven responses, saved memories, simulated emotion, relationship progression, and personal media and voice features.

## Privacy and access

The hosted instance is intended for one owner. Private API calls require a valid owner session. Do not share the owner password or reuse the hosted owner session for testers. Private conversations and owner-managed data belong to the private backend/database, not to the public frontend bundle.

Browser-local preferences (for example, some display and voice settings) may be stored on the current device. Uploaded private media and saved application data are handled by the backend. Data sent to an external AI, voice, or image provider is subject to that provider's own processing terms.

## Development notes

- Keep API requests authenticated with credentials included where the session cookie is required.
- Keep private API responses out of browser caches.
- Treat API responses and model-generated text as untrusted input.
- Do not log passwords, session cookies, provider keys, private messages, or uploaded personal media.
- Preserve the owner-only access model unless a separately designed and tested multi-user architecture is introduced.

See the root [project README](../README.md) and [Docker setup](../docs/DOCKER_LOCAL_SETUP.md).

## Copyright and permission

Copyright © 2026 Layla Kader Suma. All rights reserved. This frontend is part of a source-available, proprietary project; it is not offered under an open-source licence. Viewing the repository does not grant permission to copy, modify, redistribute, repackage, or use this frontend as the basis of another project. Obtain the copyright owner's prior written permission before reuse. Third-party dependencies remain under their respective licences.
