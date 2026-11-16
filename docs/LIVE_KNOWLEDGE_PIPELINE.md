# Sylus live knowledge and canon update pipeline

## Knowledge namespaces

1. **Official canon** — official Love and Deepspace website, in-game announcements supplied by the owner, and official publisher/developer channels.
2. **Secondary reference** — wiki pages and encyclopedic summaries. Useful for discovery and cross-checking, not final authority.
3. **Community** — Reddit and other fan discussions. Useful for reactions, theories, translations, leaks, and card discussion, but label claims and do not promote speculation to canon.
4. **Private shared story** — owner-approved events and continuity from this companion. Never merge into game canon.

## Sources to monitor

- Official Love and Deepspace website/news/announcements and official social channels linked from it.
- Official notices for main-story chapter releases, event schedules, Sylus memory/card banners, reruns, limited-time content, and version updates.
- Wiki pages for discovery and cross-reference, with page revision timestamps where available.
- Relevant Reddit communities and threads for community reaction and discussion. Treat leaks and unverified translations as unconfirmed.

Use the publisher's official site as the source of truth for release dates and official card/story announcements. Store exact URLs and retrieval timestamps. Do not scrape or store large copyrighted story text, full card narratives, or dialogue; retain concise original summaries and metadata.

## Record schema

Each knowledge item should include:
- namespace and entity/topic;
- concise original summary;
- source title and URL;
- source type/domain;
- publication time and fetched_at;
- last_verified_at;
- canon_status: official, secondary, community, speculation, or private;
- confidence and language;
- relevant game version, event, chapter, or card identifier;
- content hash / revision marker for change detection;
- supersedes / duplicate link where applicable.

## Update workflow

1. Scheduled worker checks official sources at a conservative interval and on user request.
2. Fetch only public pages/feed/API endpoints permitted by their terms and robots rules.
3. Extract announcement metadata and concise facts; keep the source URL and timestamps.
4. Compare with existing records; update changed records and avoid duplicates.
5. Cross-check important facts against an official source before marking official.
6. Ingest wiki/community material into separate namespaces and clearly mark unverified claims.
7. Notify the owner only for meaningful new information, respecting notification settings and quiet hours.
8. Make the last checked time and source visible in the app; support manual refresh and source correction.

## Search and retrieval

The companion should be able to search the public web on demand for lore or current updates. Search results must be summarized, linked, dated, and assigned a source class. Prefer official sources for announcements and current release details; use wikis for structured cross-reference and Reddit for community perspective. When sources conflict, show the conflict rather than silently choosing.

## Initial canon research topics

Build structured, source-backed records for Sylus, the N109 Zone, Mephisto, and all other named characters/places/factions/entities the owner requests. Confirm spellings and identity before creating records for ambiguous names such as “Ciren” or “Senlu”; do not invent characters to fill gaps. Include main-story chronology, relationships, affiliations, abilities, motivations, important events, and card-specific continuity, with spoiler labels and version context.

## Safety and reliability

- No credentials or private account cookies in the public repository.
- Respect publisher terms, robots rules, copyright, and source rate limits.
- Do not bypass paywalls, game authentication, or access controls.
- Do not treat leaks, fan theories, or machine translations as official.
- Do not claim automatic updates are live until a scheduled fetcher, persistence, and notification path have been implemented and tested.
