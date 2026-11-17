# Private Render preview setup

This repository includes a Render Blueprint and a single-container Dockerfile for a hosted preview. It serves the React PWA and FastAPI API from the same origin, while PostgreSQL stays external and persistent.

## Why this preview uses Neon for PostgreSQL

Do not use Render's Free Postgres for SYLUS memory or chat history: Render documents that Free Postgres expires 30 days after creation and has no backups. The preview instead expects a Neon Postgres connection string. Neon Free currently includes 100 CU-hours per project per month, 1 GB Postgres storage per project, 5 GB monthly public network transfer, and compute that scales to zero after 5 minutes. It is suitable for a small preview, not a production backup strategy.

## Setup

1. Create a Neon account and a Postgres project named `sylus-private`. Choose Singapore or the closest Asia-Pacific region available.
2. Copy the pooled connection string from Neon. Keep it private; it becomes the Render `DATABASE_URL`.
3. Create API keys only for providers whose free tier you intend to use. Gemini is the default for ordinary chat; Groq is first for mature romantic/intimate chat. Optional free-tier fallbacks are Aion Labs, OpenRouter free models, Mistral Free mode, Cloudflare Workers AI Free, and Cohere trial. Do not attach payment methods, buy credits, or enable billing. Never paste keys into ChatGPT or commit them.
4. Connect the GitHub repository to Render.
5. Create a Blueprint from the repository's `render.yaml` and inspect the proposed plan.
6. Before applying, confirm the service is a Free web service in Singapore and that no Render Postgres database or paid resource is being created.
7. After applying the Blueprint, set these manual variables in the Render service's Environment page:
   - `DATABASE_URL`: your Neon pooled connection string
   - `SYLUS_OWNER_PASSWORD`: a unique, strong password used only for SYLUS
   - `GEMINI_API_KEY`: optional Gemini Free-tier key (ordinary chat primary)
   - `GROQ_API_KEY`: optional Groq Free-plan key (mature chat primary)
   - Add any other free-tier keys from `backend/.env.example` only if you can use them without a payment method
   - Leave all provider keys blank to keep the app in no-chat preview mode
8. Render generates `SYLUS_OWNER_TOKEN` and `SESSION_SECRET`. Do not replace them with reused passwords.
9. Wait for the deploy and open the Render service URL. Sign in from Settings with your owner password.

The app applies migrations at startup. The Render deployment serves the PWA from FastAPI. The service worker caches only the static app shell and never caches `/v1/*) API responses.

## Free-preview limitations

- Render Free web services spin down after 15 minutes without traffic and can take about one minute to wake up. They have an ephemeral filesystem.
- Neon Free has 100 CU-hours and 1 GB storage per project; its compute scales to zero after 5 minutes. It has no scheduled backups on the Free plan.
- Export your database before any significant changes. Do not treat the free preview as the permanent home for irreplaceable memories or chat history.
- The preview does not provide autonomous messages/calls while the web service is asleep. Scheduler, push notifications, voice, image generation, and Android native packaging are not implemented.
- The GitHub repository is public. Keep all environment values and personal data out of commits.

## Before production

Use an always-on service, a paid database plan with automated backups or a tested backup routine, HTTPS, spending limits, monitoring, and a verified restore procedure. Review the Groq data boundary in `CHAT_MODEL_PROVIDER.md). No paid model fallback is enabled.
