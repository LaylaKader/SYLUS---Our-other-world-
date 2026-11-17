-- Seed the initial character reference database so lore retrieval has usable records.
-- These are secondary-reference summaries, not official source text. Keep their provenance visible.

INSERT INTO character_knowledge_records
(namespace, topic, summary, source_url, canon_status, confidence, language)
SELECT 'secondary', 'Mephisto — identity and origin',
'Mephisto is Sylus’s mechanical crow companion, created by Sylus. He is not an ordinary bird or a generic disposable drone: he has a recognizable crow-like presence and an established place in Sylus’s daily world. When asked who Mephisto is, identify him directly as Sylus’s mechanical crow companion rather than claiming the character is unknown.',
'https://loveanddeepspace.fandom.com/wiki/Mephisto', 'secondary', 0.88, 'en'
WHERE NOT EXISTS (
  SELECT 1 FROM character_knowledge_records
  WHERE topic = 'Mephisto — identity and origin'
);

INSERT INTO character_knowledge_records
(namespace, topic, summary, source_url, canon_status, confidence, language)
SELECT 'secondary', 'Mephisto — role and capabilities',
'Mephisto is used for observation, surveillance, reconnaissance, and carrying or delivering messages. Do not portray him as omniscient or as having unrestricted access to private devices and networks. Describe only capabilities supported by the story; do not invent technical specifications.',
'https://loveanddeepspace.fandom.com/wiki/Mephisto', 'secondary', 0.82, 'en'
WHERE NOT EXISTS (
  SELECT 1 FROM character_knowledge_records
  WHERE topic = 'Mephisto — role and capabilities'
);

INSERT INTO character_knowledge_records
(namespace, topic, summary, source_url, canon_status, confidence, language)
SELECT 'secondary', 'Mephisto — personality and relationship with Sylus',
'Mephisto has a distinct, clever, temperamental personality with recognizable crow-like habits, including interest in shiny objects. Sylus’s interactions with him can carry dry familiarity and exasperation as well as trust; do not reduce their relationship to owner and ordinary pet. Keep the portrayal grounded and avoid inventing private scenes.',
'https://loveanddeepspace.fandom.com/wiki/Mephisto', 'secondary', 0.82, 'en'
WHERE NOT EXISTS (
  SELECT 1 FROM character_knowledge_records
  WHERE topic = 'Mephisto — personality and relationship with Sylus'
);

INSERT INTO character_knowledge_records
(namespace, topic, summary, source_url, canon_status, confidence, language)
SELECT 'secondary', 'Sylus — Onychinus and N109 Zone',
'Sylus is associated with Onychinus and holds significant influence in the N109 Zone. His world involves Protocore-related dealings, dangerous networks, and competing interests. Do not assume that every person or event in the Zone is under his direct control.',
'https://loveanddeepspace.wiki.gg/wiki/Sylus', 'secondary', 0.84, 'en'
WHERE NOT EXISTS (
  SELECT 1 FROM character_knowledge_records
  WHERE topic = 'Sylus — Onychinus and N109 Zone'
);

INSERT INTO character_knowledge_records
(namespace, topic, summary, source_url, canon_status, confidence, language)
SELECT 'secondary', 'Luke and Kieran — Sylus’s associates',
'Luke and Kieran are twin brothers and close associates working with Sylus. Luke is generally the more energetic and unpredictable twin, while Kieran is more measured and dependable. Their masks can make them difficult to distinguish, and their banter includes mischief, but they are capable operatives rather than incompetent comic relief.',
'https://loveanddeepspace.wiki.gg/wiki/World_Underneath/Mischief', 'secondary', 0.80, 'en'
WHERE NOT EXISTS (
  SELECT 1 FROM character_knowledge_records
  WHERE topic = 'Luke and Kieran — Sylus’s associates'
);
