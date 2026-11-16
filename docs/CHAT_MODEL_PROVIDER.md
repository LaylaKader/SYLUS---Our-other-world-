# Chat model provider and data boundary

## Initial adapter configuration
The server-side adapter is OpenAI-compatible. The sample configuration points to GroqCloud:
- Base URL: `https://api.groq.com/openai/v1`
- Sample model: `openai/gpt-oss-120b`
- Key location: backend environment only (`MODEL_API_KEY`)

This is a configurable starting point, not a hard dependency. No key is bundled in the frontend or repository. No alternate provider or paid fallback is selected automatically. If the key is absent or the configured model is unavailable, the app returns an error rather than switching to a paid service.

## What leaves the private server
For a normal chat reply, the server sends the current message, up to 12 recent user/assistant messages (each clipped to 1,800 characters), the Sylus persona instructions, up to five retrieved non-sensitive memory records (each clipped to 1,000 characters) to the configured model provider. The private chat database remains under the app owner's database control, but prompts are processed by the external provider. Do not send highly sensitive information until you have reviewed the provider's current terms and data controls.

Sensitive memories are excluded from retrieval, but sensitive content written in ordinary chat history may still be included in the recent-message context. This is a known limitation; a future per-conversation privacy filter should be added.

The response is capped at 800 output tokens. This bounds accidental long generations and helps keep free-tier token use predictable.
- Groq says inference requests are not retained by default. It may temporarily log inputs and outputs for reliability troubleshooting or abuse investigations for up to 30 days; its Data Controls page describes Zero Data Retention (ZDR), which disables this temporary customer-data storage: https://console.groq.com/docs/your-data
- Groq's services agreement says it does not use customer inputs or outputs to train or fine-tune models unless the customer explicitly permits or instructs it: https://console.groq.com/docs/legal/services-agreement
- Groq states retained customer data is stored in GCP buckets in the United States. Review its current terms and data controls before using it: https://console.groq.com/docs/your-data
- Free-tier quotas are model- and organization-specific and may change. The official rate-limit page is authoritative for the account's current quotas: https://console.groq.com/docs/rate-limits
- ## Current provider documentation checked 2026-11-17
- Groq's current supported-model documentation lists `openai/gpt-oss-120b` as a featured model: https://console.groq.com/docs/models
- The current Free-plan rate-limit table lists `openai/gpt-oss-120b` with 30 requests/minute, 1,000 requests/day, 8,000 tokens/minute, and 200,000 tokens/day as the published Free-plan limits. Check the Groq Console before relying on these figures.

A free API is not the same as local/offline inference. If the data boundary is not acceptable, do not configure an external key; chat remains disabled until another provider or a self-hosted model is selected.
