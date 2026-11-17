# SYLUS chat providers: free-tier routing

## Routing policy

The backend uses only explicitly configured providers and the model IDs listed below. It never selects a paid model or silently enables billing.

- Ordinary conversations: Gemini Flash → Groq → Aion Labs RP → OpenRouter free router → Cloudflare Workers AI free model → Cohere trial.
- Mature romantic/intimate conversations: Groq → Aion Labs RP → an explicitly configured OpenRouter model only when its own provider/model terms permit the content. Gemini is intentionally excluded from this route.
- A provider that returns 429, 402, 403, or another error is skipped; the backend does not retry an exhausted quota. It proceeds to the next eligible provider.
- The provider chain is best-effort, not unlimited. Every free tier has quotas and can change or become unavailable.
- Mature routing is a simple keyword/context classifier, not a perfect content classifier. Provider safeguards and terms still apply; routing does not bypass them.

## Optional environment variables

All keys are server-side secrets. Never put them in frontend code, commit them, or paste them into chat.

| Provider | Environment variables | Free model / tier |
|---|---|---|
| Google Gemini | `GEMINI_API_KEY`, `GEMINI_MODEL`, `GEMINI_FALLBACK_MODEL` | `gemini-3.8-flash` → `gemini-3.5-flash-lite`; Free tier only |
| Groq | `GROQ_API_KEY`, `GROQ_MODEL`, `GROQ_FALLBACK_MODEL` | `openai/gpt-oss-120b` → `openai/gpt-oss-20b`; Free plan only |
| Aion Labs | `AION_API_KEY`, `AION_MODEL` | `aion-labs/aion-rp-llama-3.1-8b`; default Free tier |
| OpenRouter | `OPENROUTER_API_KEY`, `OPENROUTER_MODEL` | `openrouter/free`; free-model routing only |
| Cloudflare Workers AI | Existing `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_API_TOKEN`, plus `CLOUDFLARE_CHAT_MODEL` | `@cf/meta/llama-3.1-8b-instruct-fp8-fast`; Workers Free allowance only |
| Cohere | `COHERE_API_KEY`, `COHERE_MODEL` | `command-a-03-2025`; trial/evaluation key only |

Legacy `MODEL_API_BASE_URL`, `MODEL_API_KEY`, and `MODEL_NAME` remain supported for the existing Groq connection.

## Free-tier caveats checked 18 November 2026

- Gemini API: Free tier is limited to eligible models and project-specific quotas shown in Google AI Studio. Google says content submitted on the free tier may be used to improve its products. Do not use this provider for conversations you do not want processed under those terms. Do not attach a billing account.
- Groq: Free-plan limits are model- and organization-specific. The Free plan publishes separate per-model limits for `openai/gpt-oss-120b` and `openai/gpt-oss-20b`: 1,000 requests/day and 200,000 tokens/day, with 8,000 tokens/minute. Quotas can vary by account. The smaller model is used as a second Groq lane when the primary model is exhausted.
- Aion Labs: the default Free tier publishes 15 requests/minute and 20,000 tokens/day. Free access is described as a courtesy that may change; do not top up credits.
- OpenRouter: free model variants have a 20 requests/minute and 50 requests/day cap. The 1,000/day increase requires buying credits, so it is not used here.
- Mistral is excluded: its official API quickstart requires billing/payment activation before API keys work.
- Cloudflare Workers AI: Workers Free includes 10,000 Neurons/day. Requests stop when the free allocation is exhausted; do not upgrade to Workers Paid or buy AI Gateway credits.
- Cohere: trial keys are free but limited to 1,000 calls/month and are intended for evaluation/prototyping, not a high-volume production service.

SambaNova is deliberately excluded because its current Plans page says a payment method and credit purchase are required to run first requests. Cerebras is excluded because it requires a payment method for its current offer. NVIDIA NIM is excluded from this hosted app because its no-charge offering is for exploration/development rather than dependable production inference. Alibaba Cloud's free quota can automatically bill after exhaustion unless Free Quota Only is explicitly enabled, so it is not configured.

## Privacy and memory

For each reply, the provider receives the current message, a bounded recent conversation history, the Sylus persona, and retrieved non-sensitive memories. The database remains under the app owner's control, but prompts are processed by the selected external provider. Sensitive memories are excluded from retrieval; sensitive content in ordinary chat history may still be included in the recent context. Provider selection does not make external processing private or local.

The memory-extraction step skips mature/intimate messages. It should never send those messages to Gemini as a side task.

## Provider references

- Gemini pricing and free-tier data policy: https://ai.google.dev/gemini-api/docs/pricing
- Gemini model list: https://ai.google.dev/gemini-api/docs/models
- Groq rate limits: https://console.groq.com/docs/rate-limits
- Groq acceptable-use policy: https://console.groq.com/docs/legal/ai-policy
- Aion Labs rate limits: https://www.aionlabs.ai/docs/rate-limits/
- Aion Labs terms: https://www.aionlabs.ai/terms/2026-10-17/
- OpenRouter pricing/free limits: https://openrouter.ai/pricing
- Mistral billing prerequisite: https://docs.mistral.ai/getting-started/quickstarts/admin/manage-workspaces
- Cloudflare Workers AI pricing: https://developers.cloudflare.com/workers-ai/platform/pricing/
- Cohere trial limits: https://docs.cohere.com/v2/docs/rate-limits
- SambaNova Plans: https://cloud.sambanova.ai/plans

## No-paid guarantee

The application does not have a billing integration and never chooses a paid model ID. However, a provider can still bill an account if its owner independently enables billing or attaches a payment method. Keep every provider account on its no-payment free tier, do not add a card, do not buy credits, and remove any paid-tier API keys. If a provider's dashboard requires payment to activate an API key, leave that provider unconfigured.
