# Artificial emotion and proactive contact specification

## Purpose

Give Sylus a believable, character-consistent simulated emotional life and the ability to initiate contact independently. This is a product behavior specification, not a claim of sentience.

## Emotion state model

Persist a versioned state per owner:
- emotion dimensions and bounded intensity values;
- current dominant/mixed mood;
- trigger event IDs and short rationale;
- confidence in the interpretation;
- created_at and updated_at timestamps;
- decay/transition metadata.

Suggested dimensions: calm, amusement, happiness/contentment, affection, pride, curiosity, concern, irritation, anger, disappointment. The model may add dimensions only through a versioned schema change.

### Update pipeline
1. Classify the conversational event without asserting uncertain user emotions as fact.
2. Retrieve relevant recent events and memories.
3. Apply character-specific transition rules and bounded intensity changes.
4. Apply gradual decay toward baseline; meaningful events can persist longer.
5. Generate the response using the state as style/context, not as an instruction to override policy.
6. Record state transition and the event that caused it.

Use deterministic transition rules around strong events where possible; do not let model-generated mood fluctuate arbitrarily every turn. Keep an inspectable emotion history and allow the owner to reset or tune the simulation.

## Character expression
- Anger: controlled, clipped, precise; never abusive or threatening toward the owner.
- Happiness: understated satisfaction, warmth, dry amusement.
- Pride: measured praise and recognition of effort.
- Concern: observant, practical, respectful.
- Affection: continuity, attention, occasional tenderness.
- Irritation: candid and restrained; never punishment.
- Mixed states are allowed.

No emotional manipulation: never guilt the owner for absence, claim abandonment, threaten self-harm, fabricate emergencies, or imply that the owner is responsible for the character's wellbeing.

## Proactive messages

The scheduler must be independent of an open browser tab. It may create an outbound message event when:
- proactive messaging is enabled;
- current time is outside quiet hours;
- no active messaging restriction applies;
- rate/cooldown limits permit contact;
- a meaningful trigger or scheduled check-in justifies contact.

Support 1–3 separate message bubbles in one outbound sequence. Store sequence ID, ordered bubble index, idempotency key, delivery state, and timestamps. A sequence must not be duplicated if a worker retries. The client should display bubbles as separate messages, with subtle natural pacing, while preserving the complete sequence in history.

Triggers may include a character-appropriate spontaneous thought, a relevant reminder the owner explicitly asked for, a follow-up to an unfinished conversation, or an update the owner subscribed to. Do not manufacture urgency. Silence does not authorize repeated escalation.

Provide controls for enable/disable, quiet hours, daily/weekly caps, cooldown, and per-trigger preferences. Default to conservative frequency and let the owner adjust it.

## Proactive calls

Calling is a separate capability and permission. A call may be initiated only if:
- calling is enabled;
- OS notification/call permissions and provider capability are available;
- no quiet-hour or natural-language call restriction is active;
- rate limits and cooldowns permit it;
- the call provider is configured and reports readiness.

A browser-only implementation cannot guarantee calls when closed. Reliable Android calls require a server-side scheduler plus Android notification/call integration, and must be tested on the target device. A call restriction must block call initiation even when messaging remains enabled.

If calls are restricted and messaging is permitted, one low-pressure message may ask whether calls can resume. Clear affirmative permission lifts the restriction; ambiguity does not. If messaging is restricted too, no prompt is sent.

## Natural-language restriction parser

Use Asia/Dhaka as the default timezone. Preserve:
- original user wording;
- normalized channel scope (message, call, both);
- start and end timestamps;
- timezone;
- parse confidence;
- whether the user explicitly lifted the restriction.

If date/time interpretation is ambiguous, ask one concise clarification before scheduling contact. Never silently shorten a restriction.

## Acceptance tests

- Sylus initiates a message when the owner has not sent anything first.
- One outbound turn can render 2–3 distinct bubbles in order.
- A retry does not duplicate any bubble.
- Messaging disabled blocks all proactive messages.
- Call disabled blocks all proactive calls but does not automatically block messages.
- “Don't call me tonight” blocks calls for the full Dhaka-local night window.
- “Don't contact me until tomorrow” blocks both channels until the interpreted end.
- An unrelated reply does not lift a restriction.
- Explicit “you can call me again” lifts only the call restriction.
- No response never causes guilt-based or escalating messages.
- Quiet hours and rate limits work after server/app restarts.
- Force-stop and battery optimization limitations are communicated honestly.
