# Sylus knowledge source registry

The knowledge pipeline must keep official canon, community-maintained reference, speculation, and private shared-story memory separate.

## Source tiers

1. **Official primary sources** — Infold's Love and Deepspace website/news, verified official social accounts, official YouTube/Discord announcements, and in-game text/media supplied by the owner. Highest authority for release dates, event details, official story announcements, and card information.
2. **Community reference sources** — Love and Deepspace Wiki (wiki.gg), Fandom wiki, and community databases. Useful for indexing characters, locations, timelines, and card catalogues. Treat as secondary sources and retain their citations.
3. **Community discussion** — Reddit and other fan discussions. Useful for theories, reactions, interpretation, translations, and early leads. Never silently promote an unverified claim to canon.
4. **Private shared continuity** — the user's conversations, approved memories, and shared roleplay events. This is not game canon and must never be published to public knowledge.

## Initial sources

- Official English website/news: https://loveanddeepspace.infoldgames.com/en-EN/home
- Official English news index: https://loveanddeepspace.infoldgames.com/en-EN/news
- Official YouTube channel: https://www.youtube.com/@LoveandDeepspace
- Official X account: https://x.com/Love_Deepspace
- Community wiki (wiki.gg): https://loveanddeepspace.wiki.gg/wiki/Love_and_Deepspace_Wiki
- Community wiki (Fandom): https://loveanddeepspace.fandom.com/wiki/Love_and_Deepspace_Wiki
- Reddit community: https://www.reddit.com/r/LoveAndDeepspace/

## Ingestion and update rules

- Check official news and official social announcements on a scheduled basis; use RSS/sitemaps/page polling where available and record the last successful check.
- Watch for main-story branch announcements, version updates, Sylus memory/card announcements, reruns, event windows, and maintenance notices.
- Use official source content as the authoritative record for names, dates, server time, card availability, and event rules.
- Community wikis can fill structured lore gaps, but store source URL, retrieval timestamp, page revision/update timestamp when available, and confidence.
- Reddit may suggest leads or interpretations. Save those as community discussion with author/post URL and timestamp; require official corroboration before marking canon.
- Never scrape private or access-controlled content. Respect robots.txt, rate limits, copyright, and platform terms. Store concise factual summaries and metadata rather than copying large passages, full story chapters, or card dialogue.
- Detect conflicting claims and preserve both source records; prefer newer official sources for current events.
- All event dates must retain their stated server timezone. Display converted local time separately as Asia/Dhaka and label it as a conversion.
- Each knowledge record has a status: `official`, `secondary`, `community`, `speculation`, or `private_shared_story`.
- The agent should say when information is unverified or stale rather than confidently improvising.

## Initial lore anchors

The official website is the source of truth for new releases and announcements. Community reference pages currently identify Sylus as the leader of Onychinus in the N109 Zone and Mephisto as his mechanical crow/intelligence aide. Treat these as secondary until verified against in-game/official material. The exact names "Ciren" and "Senlu" supplied by the owner need spelling/source confirmation before creating canon entries; do not silently guess who they refer to.

## Update scheduler requirements

A later worker should:
1. Poll official news and announcements on a configurable cadence.
2. Deduplicate by canonical URL and stable content hash.
3. Extract structured entities (character, memory/card, branch, event, date/time, version).
4. Save source and status before notifying Sylus.
5. Notify the user only for relevant Sylus/main-story updates, not every general game post.
6. Keep a manual refresh action and show last checked / last successful sync.
