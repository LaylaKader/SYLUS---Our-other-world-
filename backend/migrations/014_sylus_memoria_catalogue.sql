-- Sylus Memoria title catalogue: title recognition is separate from plot knowledge.
-- Individual plot summaries should be added as their own source-backed records.
INSERT INTO character_knowledge_records
(namespace, topic, summary, source_title, source_url, canon_status, confidence, language, event_key)
SELECT
  'secondary',
  'Sylus Memoria catalogue — all 34 indexed date stories and card titles',
  'The following Sylus Memoria titles are indexed in the reference catalogue: Alternative Darkborne; Autumn Eyes; Chaotic Velocity; Darkbound Souls; Finale Undone; Freefall Gambit; Goodcat Code; Grassland Romance; Immobilized; Improvised Flow; Innocent Birdcage; Kitten Included; Lost Oasis; Lovespeed Ride; Magnum Opus; Night of Secrecy; Nightglow; Nightly Duet; Nightplumes; No Defense Zone; Ordinary Traces; Paradox Vector; Passionate Appraisal; Primordial Chaos; Radiant Brilliance; Rainlit Night; Rosy Hues; Searing Touch; Shared Bliss; Shared Lanterns; Tipping Point; Valleydream Bloom; Within Reach. This record is a title index, not a substitute for each individual story synopsis. If asked about a listed title, recognize it as a Sylus Memoria. Retrieve a dedicated story record when available; if no dedicated synopsis exists yet, be honest that the title is known but the detailed plot has not yet been verified. Never invent scenes or claim the card is unfamiliar solely because its plot record is missing.',
  'Category: Sylus Memoria Dates — Love and Deepspace Wiki',
  'https://loveanddeepspace.wiki.gg/wiki/Category:Sylus_Memoria_Dates',
  'secondary',
  0.94,
  'en',
  'sylus_memoria_catalogue'
WHERE NOT EXISTS (
  SELECT 1 FROM character_knowledge_records
  WHERE topic = 'Sylus Memoria catalogue — all 34 indexed date stories and card titles'
);
