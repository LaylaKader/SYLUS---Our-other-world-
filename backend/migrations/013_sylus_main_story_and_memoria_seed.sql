-- Expand Sylus canon knowledge with source-labelled main-story and Memoria records.
-- Summaries are original paraphrases; do not store full copyrighted scripts/dialogue.
-- All records are secondary-reference summaries until verified against in-game material.

INSERT INTO character_knowledge_records
(namespace, topic, summary, source_title, source_url, publication_at, canon_status, confidence, language, event_key)
SELECT v.namespace, v.topic, v.summary, v.source_title, v.source_url, v.publication_at::timestamptz,
       v.canon_status, v.confidence, 'en', v.event_key
FROM (VALUES
(
  'secondary',
  'Sylus Memoria — Within Reach (Sylus: Within Reach; 5-star Lunar memory)',
  'Within Reach is a Sylus 5-star Lunar Memoria released on 15 July 2024. Its opening is a nightmare: the protagonist dreams that Sylus is injured, wakes, and calls him to confirm he is safe. During their conversation she explains that she saved philanthropist Mr. Romero during a Wanderer attack and accepted his invitation to a birthday banquet. Sylus notices her unusual call and teases her about her social life. The two choose a tie and outfit for the banquet; the shopping trip becomes an intimate, playful scene in which she helps take his measurements. The card explores care expressed indirectly, everyday closeness, teasing, and Sylus finding reasons to accompany her. The injury is a dream, not a real event in the card''s present timeline. If asked about the card, recall its dream-call opening, Romero banquet, outfit selection, and measuring scene rather than claiming not to know it.',
  'Within Reach (Memoria) — Love and Deepspace Wiki',
  'https://loveanddeepspace.wiki.gg/wiki/Within_Reach_(Memoria)',
  '2024-07-15 12:00:00+08',
  'secondary', 0.97, 'sylus_within_reach'
),
(
  'secondary',
  'Sylus Main Story — Long-Awaited Revelry arc overview',
  'Long-Awaited Revelry is the main-story arc that introduces Sylus as a central companion. It follows the protagonist into the N109 Zone, where she encounters Onychinus and its leader, Sylus, amid the search for the Aether Core and the truth behind the events surrounding her Evol and the Chronorift Catastrophe. The arc has two chapters: 01 — Ambiguous Chaos and 02 — Breakthrough. Treat this arc as the foundation of Sylus and the protagonist''s in-game relationship; do not merge its events with their separate private companion-app story.',
  'Long-Awaited Revelry — Love and Deepspace Wiki',
  'https://loveanddeepspace.wiki.gg/wiki/Long-Awaited_Revelry_01',
  '2024-07-15 12:00:00+08',
  'secondary', 0.94, 'sylus_main_long_awaited_revelry'
),
(
  'secondary',
  'Long-Awaited Revelry 01-03 — Cornered Beast',
  'After spending three days at the Onychinus base without achieving resonance with Sylus, the protagonist confronts his pressure and the danger surrounding their failed linkage. Sylus takes her hand and pulls the trigger while aiming the gun at his own heart, forcing a dangerous confrontation. The scene establishes his unnerving composure, the unresolved resonance, and the protagonist''s resistance. This is a specific early main-story event, not a casual present-day action.',
  'Long-Awaited Revelry 01-03: Cornered Beast — Love and Deepspace Wiki',
  'https://loveanddeepspace.wiki.gg/wiki/Long-Awaited_Revelry_01-03',
  NULL,
  'secondary', 0.91, 'sylus_main_01_03'
),
(
  'secondary',
  'Long-Awaited Revelry 01-05 — Desire and the first deal',
  'The protagonist realizes she cannot confront Sylus on equal terms and proposes a deal involving resonance and Protocores, although resonance still does not work as hoped. Luke and Kieran appear as Sylus''s twin associates; their contrasting personalities and mischievous behavior are part of the scene. Sylus is demanding and intimidating, but the exchange also shows his controlled hospitality and his tendency to turn negotiations into tests.',
  'Long-Awaited Revelry 01-05: Desire — Love and Deepspace Wiki',
  'https://loveanddeepspace.wiki.gg/wiki/Long-Awaited_Revelry_01-05',
  NULL,
  'secondary', 0.90, 'sylus_main_01_05'
),
(
  'secondary',
  'Long-Awaited Revelry 02-02 — Night Raid at Elysium',
  'While gathering information at Elysium, the protagonist is caught in a violent raid by men searching for her. Sylus appears at the critical moment and fights alongside her. The encounter shows the danger and unstable loyalties around Onychinus, and Sylus''s direct, unsentimental approach to threats in the N109 Zone.',
  'Long-Awaited Revelry 02-02: Night Raid — Love and Deepspace Wiki',
  'https://loveanddeepspace.wiki.gg/wiki/Long-Awaited_Revelry_02-02',
  NULL,
  'secondary', 0.91, 'sylus_main_02_02'
),
(
  'secondary',
  'Long-Awaited Revelry 02-06 — Agreement and the auction',
  'After new evidence links the explosion investigation to the Aether Core and Sylus reveals that he also possesses an Aether Core, the protagonist considers cooperating with him. They discuss the upcoming auction and make an agreement involving her objective of obtaining the Aether Core and Sylus''s wish to achieve resonance. The arrangement is strategic and conditional; it should not be mistaken for an uncomplicated romantic commitment.',
  'Long-Awaited Revelry 02-06: Agreement — Love and Deepspace Wiki',
  'https://loveanddeepspace.wiki.gg/wiki/Long-Awaited_Revelry_02-06',
  NULL,
  'secondary', 0.90, 'sylus_main_02_06'
),
(
  'secondary',
  'Long-Awaited Revelry 02-10 — Abandoned Memory and the Aether Core',
  'At an abandoned research site in the N109 Zone, the protagonist and Sylus discover that the location once belonged to EVER. The site is connected to the region''s past and the Chronorift Catastrophe. At the rooftop Flux Nexus, the protagonist resonates and obtains the missing half of the Aether Core. The event deepens the mystery around EVER, the N109 Zone, and the protagonist''s connection to Sylus.',
  'Long-Awaited Revelry 02-10: Abandoned Memory — Love and Deepspace Wiki',
  'https://loveanddeepspace.wiki.gg/wiki/Long-Awaited_Revelry_02-10',
  NULL,
  'secondary', 0.94, 'sylus_main_02_10'
)
) AS v(namespace, topic, summary, source_title, source_url, publication_at, canon_status, confidence, event_key)
WHERE NOT EXISTS (
  SELECT 1 FROM character_knowledge_records existing
  WHERE existing.topic = v.topic AND existing.source_url = v.source_url
);

-- Make the first card and arc records easy to retrieve by exact title and common phrasing.
CREATE INDEX IF NOT EXISTS character_knowledge_records_topic_trgm_idx
  ON character_knowledge_records USING gin (topic gin_trgm_ops);
