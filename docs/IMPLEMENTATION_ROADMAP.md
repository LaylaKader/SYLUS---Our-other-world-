# SYLUS implementation roadmap

## Product target

A private, single-owner Android companion with a fast text-chat experience first. The app must preserve conversations and personal memories across app restarts and browser closure. Voice calling and proactive contact are part of the target; screen sharing, Together activities, and the 3D avatar are later modules.

## Repository audit — 2026-11-16

- The default branch contains a README and a partial Floot source snapshot under `backup/floot-source/`.
- The README explicitly describes this as a recovery copy, not a runnable deployment.
- The snapshot references application files that are not present in the backup, so it cannot currently be built as a standalone app.
- Existing UI includes a memory panel, chat page, voice panel, gallery, Together panel, and a small character profile. Their presence does not prove that the underlying persistence, retrieval, or call workflows are complete.
- Do not put personal memories, conversation exports, API keys, or other private data in this repository. The current repository is public.

## Architecture principles

1. Keep the app single-owner. Do not add public registration or multi-user product flows.
2. Still protect the private instance. No unauthenticated public endpoint may read or write chat, memories, media, or call preferences. Use a private access mechanism or owner-only deployment boundary.
3. Separate three data domains:
   - character canon and persona configuration;
   - personal long-term memories and relationship continuity;
   - immutable conversation/message history and attachments.
4. Store data in a persistent database, not browser local state. Add migrations, backups, restore tests, and retention controls.
5. Retrieve only relevant memories for each response. Store provenance, timestamps, confidence, and supersession links so outdated or uncertain memories are not treated as facts.
6. Keep model/provider integrations behind interfaces. No automatic paid fallback; if a configured free/local provider is unavailable or quota-limited, explain the failure rather than silently charging.
7. Keep voice, proactive messaging/calling, media, Together features, and the future 3D avatar as independent modules.
8. The 3D avatar must be a replaceable adapter (for example GLB/VRM renderer interface), so adding a model later does not require rewriting chat or memory.

## Build order and acceptance checks

### Phase A — runnable private chat foundation
- Recover or replace missing app source; establish a reproducible build and documented local run command.
- Implement owner-only access without public registration.
- Implement chat list, message send/receive, timestamps, retries, and durable server-side persistence.
- Acceptance: send messages, close/reopen the app, and verify the full conversation is still present; verify a second unauthorized device cannot read it.

### Phase B — character and memory
- Load the persona from a versioned character configuration.
- Create separate tables/collections for memories, memory links, memory events, conversations, and messages.
- Add explicit memory extraction, deduplication, conflict handling, relevance retrieval, and user review/edit/delete.
- Acceptance: test a detail saved in one conversation, retrieve it naturally in a later conversation, update a changed detail, and confirm unrelated memories are not injected.

### Phase C — voice
- Add speech input/output behind replaceable provider interfaces.
- Test microphone permission, interruption, turn-taking, latency, voice quality, and fallback behavior.
- No voice cloning or use of protected voice recordings without authorization.

### Phase D — proactive contact and calls
- Run a scheduled/background service independent of the browser tab.
- Parse natural-language contact restrictions using Asia/Dhaka time. Restrictions override autonomous contact for their full duration. Ask by message before resuming calls when permitted; if messaging is also restricted, remain silent.
- Require Android notification/call permissions and test battery/background limits on real devices.
- Acceptance: verify allowed contact, blocked contact, expiry, explicit permission to resume, and app force-stop behavior.

### Phase E — later modules
- Add screen sharing/Together activities after chat and calls are reliable.
- Add a 3D avatar through the replaceable renderer interface. Do not block the chat release on finding a model.

## Security and release gates

- Never commit secrets, private memories, chat exports, or private media.
- Use environment variables or a secrets manager for provider credentials.
- Encrypt transport; restrict database access; use private object storage for attachments.
- Test backup restoration and owner-only access before sharing a hosted link.
- A GitHub source link is not a working app link. Publish a hosting link only after a successful deployment and smoke test.
