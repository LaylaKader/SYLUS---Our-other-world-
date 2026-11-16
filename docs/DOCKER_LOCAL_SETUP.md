# Run SYLUS locally with Docker Compose

1. Install Docker Desktop or Docker Engine with the Compose plugin.
2. Copy `.env.compose.example` to `.env` in the repository root.
3. Replace the four secret placeholders with independent random values. Keep the real `.env` private.
4. Optionally add a Groq API key to `MODEL_API_KEY`. Leaving it blank lets the app start in preview mode, but chat replies return a clear configuration error. No alternate or paid provider is selected.
5. Run `docker compose up --build`.
6. Open `http://localhost:8080`; go to Settings and sign in with `SYLUS_OWNER_PASSWORD`.

The frontend is the only published container port. Nginx proxies the private API internally. PostgreSQL has a persistent Docker volume. SQL migrations are applied by the backend at startup and tracked in `schema_migrations`.

To stop: `docker compose down`. To stop without deleting data, do not add `-v`. Removing the named volume permanently deletes the local database.
