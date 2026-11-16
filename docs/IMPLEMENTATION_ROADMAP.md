# SYLUS implementation roadmap

## Product target
A private, single-owner Android companion with fast text chat, durable chat history, separate long-term memory, a consistent Sylus persona, simulated emotional continuity, source-aware live lore, and proactive messages/calls governed by owner permissions. Screen sharing, Together activities, and a replaceable 3D avatar are later modules.

## Repository audit — 2026-11-16
- The default branch contains a partial Floot source snapshot under `backup/floot-source/`; it is a recovery copy, not a runnable deployment.
- Existing UI panels do not prove persistence, memory retrieval, voice, or calls are complete.
- The repository is public. Never commit personal memories, chat exports, API keys, private media, or provider credentials.

## Architecture principles
1. Keep the app single-owner; do not add public registration or multi-user product flows.
2. Protect the private instance. No unauthenticated public endpoint may read/write chat, memories, media, or contact preferences.
3. Separate persona/canon, private memories/shared story, and immutable conversation history.
4. Persist data in a database with migrations, backups, restore tests, and retention controls.
5. Retrieve relevant memories only; store provenance, timestamps, confidence, sensitivity, and supersession.
6. Keep model/provider integrations replaceable. No automatic paid fallback.
7. Keep voice, proactive contact, media, Together, and avatar as independent modules.
8. Future 3D avatar uses a replaceable renderer adapter (for example GLB/VRM).
9. Persist an inspectable artificial-emotion state; it shapes expression but never overrides consent or safety.
10. Separate official canon, secondary wiki reference, community discussion/speculation, and private shared-story continuity. Store provenance and freshness.
11. Sylus can initiate messages without an incoming user message; one outbound turn can contain 2–3 separate bubbles.
12. Messaging and calls have separate permissions and restrictions, interpreted in Asia/Dhaka time.
13. On-demand web research and scheduled source updates are separate capabilities; both must preserve provenance.

## Build order and acceptance checks

### Phase A — runnable private chat
- Recover/replace missing app source; establish reproducible build.
- Implement owner-only access without public registration.
- Implement send/receive, timestamps, retries, pagination, and durable persistence.
- Test history after app restart and reject unauthorized devices.

### Phase B — character and memory
- Load versioned persona configuration.
- Implement memory, memory-event, conversation, message, and knowledge stores.
- Add extraction, deduplication, conflict handling, relevant retrieval, and owner review/edit/delete.
- Test save/retrieve/update and ensure unrelated memories are not injected.

### Phase C — artificial emotion and live knowledge
- Persist emotion dimensions, transitions, confidence, and decay; feed state into text generation and later voice prosody.
- Build source-aware on-demand web research and knowledge ingestion.
- Monitor official Love and Deepspace announcements for main-story chapters, Sylus cards, reruns, events, and version notices.
- Use wikis as secondary reference and Reddit as community discussion only; label speculation.
- Test source provenance, freshness, canon separation, and mood persistence.

### Phase D — proactive messages and calls
- Implement a server-side scheduler independent of the browser tab.
- Support spontaneous messages and 1–3 bubbles per composed turn, with idempotent delivery, cooldowns, quiet hours, and owner controls.
- Parse natural-language contact restrictions using Asia/Dhaka time. Messaging and calls are separate permissions; restrictions apply for their full duration.
- Add Android notification/call integration and test background behavior on a real device.
- Test outbound messages without a user prompt, ordering, duplicate prevention, and all restrictions.

### Phase E — voice
- Add speech input/output behind replaceable provider interfaces.
- Test microphone permissions, interruption, turn-taking, latency, and voice quality.
- Use only licensed/authorized voices.

### Phase F — later modules
- Add screen sharing/Together after chat and calls are reliable.
- Add 3D avatar through replaceable renderer interface.

## Security and release gates
- Never commit secrets, private memories, chat exports, or private media.
- Use environment variables or a secrets manager for provider credentials.
- Encrypt transport; restrict database access; use private object storage.
- Test backup restoration and owner-only access before hosting.
- A GitHub source link is not a working app link; do not claim deployment until built and smoke-tested.
