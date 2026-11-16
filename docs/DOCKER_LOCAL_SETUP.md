# Run SYLUS locally with Docker Compose

1. Install Docker Desktop or Docker Engine with the Compose plugin.
2. Copy `.env.compose.example` to `.env` in the repository root.
3. Replace the four secret placeholders with independent random values. Keep the real `.env` private.
4. If you want live replies, create an API key in your own GroqCloud account and place it in `MODEL_API_KEY` in your local `.env` file. Do not paste the key into ChatGPT, GitHub, or the frontend. The configured model is `openai/gpt-oss-120b`. Leaving the key blank lets the app start in preview mode, but chat replies return a clear configuration error. No alternate or paid provider is selected.
5. Run `docker compose up --build`.
6. Open `http://localhost:8080`; go to Settings and sign in with `SYLUS_OWNER_PASSWORD`.

The frontend is the only published container port. The Nginx reverse proxy applies separate request limits to login, chat, and general API routes. Nginx proxies the private API internally. PostgreSQL has a persistent Docker volume. SQL migrations are applied by the backend at startup and tracked in `schema_migrations`.

To stop: `docker compose down`. To stop without deleting data, do not add `-v`. Removing the named volume permanently deletes the local database.
