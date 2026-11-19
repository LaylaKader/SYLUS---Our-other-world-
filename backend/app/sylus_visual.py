"""Prompt construction for stable Sylus visual continuity.

The configured Cloudflare FLUX.1-schnell endpoint is text-to-image, not image-to-image.
Owner reference photos are therefore summarized into text and used as guidance; they are
not passed as visual conditioning inputs to this model.
"""

from __future__ import annotations

import re

SYLUS_VISUAL_CANON = """
SUBJECT LOCK — SYLUS, ONE CONSISTENT FICTIONAL ADULT MAN:
Depict one adult male character only. He is unmistakably masculine, tall and lean-athletic,
with mature adult proportions, broad but not exaggerated shoulders, a defined neck and
natural human anatomy. Never change his sex or gender presentation; never create a woman,
girl, feminine substitute, second character, or generic silver-haired model.

FACE IDENTITY:
A refined, handsome, mature masculine face with a gently long oval structure, defined
cheekbones, a clean tapered jaw and firm chin; straight narrow bridge and defined nose tip;
naturally shaped lips with a subtle cupid's bow; strong, tidy, slightly angled silver brows.
Keep facial proportions balanced and consistent between images. Do not feminize the face,
round it into a childlike face, exaggerate the jaw, or turn him into a generic idol.

EYES / AETHER CORE:
Narrow, slightly elongated almond-shaped eyes with a composed, confident gaze and vivid
deep crimson-red irises. Preserve realistic pupils, darker limbal rings and subtle red
gradation rather than flat glowing discs. His RIGHT eye is associated with the Aether Core;
when the scene calls for active power, use a restrained red glow or luminous detail in that
eye only. Do not randomly make both eyes neon, pink, or different colours.

HAIR SIGNATURE:
Silver-white to cool platinum hair, never pure paper-white, blond, grey-brown or blue.
Dense, layered, feathered and deliberately tousled styling. The crown has lifted, airy,
separated locks with fine strand texture; the fringe is long and side-swept, with several
distinct tapered wisps crossing the forehead and sometimes partially veiling one eye.
Sides are shorter and layered around the temples and ears; the back has slightly longer
pieces at the nape. Use many fine, individually readable strand groups, natural flyaways,
soft highlights and cool shadow separation. Keep the same recognizable silhouette; do not
replace it with a bob, long flowing hair, a buzz cut, a smooth helmet, or random spikes.

SKIN / RENDER:
Fair, cool-neutral skin with subtle natural warmth, realistic pores and soft subsurface
scattering. Premium Love and Deepspace-like high-end 3D game character rendering; realistic
facial anatomy, expressive micro-expression, detailed hair and fabric, cinematic lighting.
Not a real person, not a photograph of a human actor, not chibi, not flat 2D anime.

WARDROBE LANGUAGE:
His wardrobe is varied, but tailored, mature and intentional. Suitable looks include:
black fitted shirts and trousers; black or deep-burgundy leather jackets; long charcoal,
black or dark-brown coats; sharply tailored black, charcoal, slate-blue or burgundy suits;
white or ivory open-collar shirts; waistcoats and layered shirts; refined high collars;
dark knitwear; restrained harness or strap details; gloves; understated metal jewellery;
and occasional casual looks such as an orange overshirt over a graphic tee. White/ivory
shirts, pale tailored coats and soft knitwear are also valid. Match the requested outfit
rather than defaulting every time to the same black suit. Clothing must fit a tall adult
male body naturally, with believable seams, collars, cuffs, folds and materials.

STYLE / COMPOSITION:
Keep the requested pose, expression, camera angle, setting and outfit. Expressions can
range from his characteristic restrained smirk, composed confidence and teasing amusement
to focused intensity, quiet tenderness, concern or genuine surprise. Do not force a smirk
into every image. Keep hands anatomically plausible. One Sylus only unless the user
explicitly requests a collage or multiple views.

NEGATIVE CONSTRAINTS:
No woman, female body, breasts, feminine face, girl, child, teen, duplicate person, extra
face, random red-eyed white-haired stranger, generic fantasy elf, cat ears, horns, chibi,
plastic skin, exaggerated muscles, malformed hands, extra fingers, text, watermark, logo,
or UI.
""".strip()


def build_sylus_image_prompt(
    user_prompt: str,
    identity_notes: str = "",
    reference_notes: list[str] | None = None,
) -> str:
    """Combine the requested scene with stable identity notes and owner-labelled references."""
    clean_request = re.sub(r"\\s+", " ", (user_prompt or "").strip())
    notes = []
    for note in [identity_notes, *(reference_notes or [])]:
        clean = re.sub(r"\\s+", " ", str(note or "")).strip()
        if clean and clean not in notes:
            notes.append(clean[:700])
    # Keep the requested scene first, then concise owner evidence, then the stable guide.
    evidence = " ".join(notes)[:1100]
    prompt = (
        f"SCENE REQUEST (follow this, including outfit, pose and expression): {clean_request}. "
        f"OWNER-APPROVED SYLUS REFERENCE NOTES: {evidence or 'Use the fixed visual identity guide below.'}. "
        f"{SYLUS_VISUAL_CANON}"
    )
    return prompt[:2048]
