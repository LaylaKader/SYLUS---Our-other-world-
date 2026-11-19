# SYLUS — A World of Our Own

**A private, single-owner AI companion built as an ongoing full-stack engineering project.**

SYLUS is a personal companion application centred on persistent conversation, a character-specific persona, relationship-state tracking, and a private space for memories and shared media. It is designed for one owner, not as a public multi-user chatbot service.

> **Status:** Active development / private beta. Features and provider availability can change as the system is tested. This repository documents the implementation honestly; it is not a claim that every module is production-ready.

## Live preview

The hosted application is available at:

**https://sylus-companion-private-gbcz.onrender.com**

The link opens the application interface. Access to private conversations and owner data requires the configured owner login. There is no public self-service registration.

## What the project includes

### Companion experience
- Character-specific Sylus persona and conversation instructions.
- Chat interface with saved conversation history.
- Multi-bubble replies and message editing.
- Persistent relationship/bond state and simulated emotional state.
- Dhaka-local time context and N109 time context.
- Proactive messaging and in-app call invitation workflows, subject to scheduler, provider, browser, and deployment availability.

### Personal space
- Owner-managed memories (create, review, edit, and delete).
- Private sticker collection and Sticker Studio.
- Image and media presentation in conversations.
- Gallery, relationship overview, and call-history areas.
- Personal settings and owner-controlled contact preferences.

### AI and backend
- FastAPI backend with an OpenAI-compatible provider adapter and configurable provider credentials.
- Prompt and context construction for persona consistency, memory grounding, and incoming media.
- Provider fallback/error handling that is being actively refined.
- PostgreSQL persistence with versioned SQL migrations.
- Owner authentication using a signed, HttpOnly session cookie or server-side bootstrap token.
- Private API routes protected by owner-session authentication.

### Frontend
- React and Vite.
- Responsive web interface with Progressive Web App (PWA) support.
- Browser-based voice interaction where supported by the device and browser.
- Frontend served with the API through the hosted deployment.

## Technology

| Layer | Technologies |
|---|---|
| Frontend | React, Vite, JavaScript, CSS |
| Backend | Python, FastAPI, Pydantic, HTTPX |
| Database | PostgreSQL, SQL migrations |
| AI integration | OpenAI-compatible chat APIs; provider configuration via server environment |
| Hosting | Render |
| Database hosting | Neon |
| Source control | Git and GitHub |

## Architecture

```text
Browser / PWA
     |
     | HTTPS
     v
Render web service
  ├── React frontend
  └── FastAPI backend
        ├── Owner authentication
        ├── Chat and persona orchestration
        ├── Memory / bond / emotion services
        ├── Media and sticker endpoints
        └── PostgreSQL connection
                 |
                 v
             Neon Postgres
```

The browser does not need direct database access. Private API requests are authenticated by the backend. Provider credentials and database credentials belong in the hosting provider's secret environment, never in frontend code.

## Repository structure

- `frontend/` — React/Vite application.
- `backend/` — FastAPI application, provider integration, and database migrations.
- `character/` — persona and character-reference material.
- `docs/` — local setup, hosting, and implementation notes.
- `docker-compose.yml` — local multi-service development setup.
- `render.yaml` — Render deployment blueprint.

## Run locally

### Docker Compose (recommended)

1. Clone the repository.
2. Copy `.env.compose.example` to `.env`.
3. Replace placeholders with unique, strong local secrets. Do not reuse passwords or production secrets.
4. Configure a model provider key only if you want to test live AI responses. Keep it server-side.
5. Start the stack:

   ```bash
   docker compose up --build
   ```

6. Open `http://localhost:8080` and sign in using the owner password configured in the environment.

For details, see the setup notes in `docs/`, `frontend/README.md`, and `backend/README.md`.

## Privacy and access

- **The live URL is not the same as public access to private data.** Anyone may be able to load the public-facing app shell, but private API operations require a valid owner session.
- There is no public sign-up flow. Do not share the owner password, bootstrap token, session secrets, database URL, or provider API keys.
- The GitHub repository is public, so source code and committed documentation can be read by anyone. Never commit `.env` files, credentials, private chat exports, personal memories, or private images.
- Chat content sent to an external AI provider is processed according to that provider's policies. Review the provider's data terms before sending sensitive information.
- The current authentication design is intended for a single owner. It is not a multi-tenant account system and should not be repurposed as one without additional isolation and security work.

## Development approach

SYLUS is developed iteratively. Small commits capture incremental changes such as UI refinements, API adjustments, prompt updates, database migrations, bug fixes, and deployment corrections. Commit count is a record of the development process; it is not a count of separate features.

## Current limitations and responsible use

This is a personal project in active development, not a production service with a formal security audit or uptime guarantee. Model-provider quotas and outages can affect response availability. Voice and notification behaviour depends on browser permissions and hosting/scheduler availability. Some modules may be incomplete or temporarily unavailable.

Before opening the service to additional users, the project would need, at minimum, multi-user authentication and data isolation, stronger abuse/rate controls, formal security review, monitored backups and restore tests, privacy disclosures, and a clear data-deletion process.

## Author

Built and maintained as an independent full-stack AI application project by **Layla Kader Suma**.

The project is an exploration of applied AI engineering, human–AI interaction, conversational memory, persona consistency, and the practical challenges of building a persistent personal companion.
