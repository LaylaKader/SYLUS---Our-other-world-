# Assistant-generated image messages

## Intended behavior
Sylus can decide that an image would add value to a conversation and send it as a separate assistant message attachment. The owner can also explicitly ask him to create an image. Images should feel contextual rather than being generated after every request.

## Generation flow
1. The agent decides whether an image is appropriate or the owner explicitly requests one.
2. Build an original image prompt using the user's request, approved style preferences, and the character visual guide.
3. Call a replaceable server-side ImageGenerator provider adapter.
4. Store the result in private object storage; keep only an opaque storage key and metadata in PostgreSQL.
5. Attach the image to an assistant message and deliver it as a normal chat item.
6. Keep the prompt/provider metadata for troubleshooting and let the owner delete the image.

## Style and character
Default Sylus imagery should follow the user's selected in-game 3D visual style, not chibi. Preserve his recognizable appearance and outfit continuity where the prompt calls for him. Use original generated scenes; do not scrape, train on, or redistribute copyrighted game assets without permission. Do not promise exact replication of game renders.

## Privacy and cost
- Provider credentials stay server-side.
- Attachments are private by default and served using owner-authorized short-lived URLs.
- No public buckets or permanent public image URLs.
- No automatic paid fallback. Show a clear error if the configured provider is unavailable or over quota.
- Make provider, cost/usage limits, image dimensions, and generation history inspectable.
- Do not silently generate images in the background if doing so incurs a charge.

## Implementation status
The database attachment table and replaceable Python interfaces are present. A real provider adapter, private object-storage implementation, chat endpoint, UI rendering, and end-to-end tests are not yet connected. Therefore image sending is specified but not yet operational.
