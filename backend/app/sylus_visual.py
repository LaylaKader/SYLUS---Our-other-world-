"""Sylus prompt builder. FLUX.1-schnell is text-to-image; private reference
photos contribute saved text descriptions, not pixel-level image conditioning."""
import re

SYLUS_VISUAL_CANON = """
Sylus from Love and Deepspace: ONE unmistakably ADULT MASCULINE man, tall and lean-athletic,
mature natural male anatomy. Refined slightly long face, defined cheekbones, tapered firm
jaw, straight narrow nose, defined lips, strong angled silver brows. Never female/feminine.

EYES: narrow elongated almond eyes, vivid deep crimson irises, dark pupils and subtle dark
limbal rings. RIGHT eye is linked to the Aether Core; restrained red glow there only when
power is active. No oversized neon eyes.

HAIR: cool silver-white/platinum, never blond. Dense layered feathered tousled cut; lifted
textured crown, distinct tapered locks, long side-swept fringe across forehead (sometimes
veiling one eye), shorter temple/ear layers, slightly longer nape. Fine separated strands,
flyaways, cool highlights/shadows. Keep silhouette; no bob, buzz cut or long flowing hair.

RENDER: fair cool-neutral skin, natural texture, premium realistic 3D game-render; believable
adult anatomy/materials. Not a real actor, chibi or flat 2D anime.

WARDROBE: match request; vary among fitted black shirts, tailored dark/burgundy/slate suits,
long dark coats, black/burgundy leather, white/ivory open-collar shirts, waistcoats, dark
knitwear, high collars, restrained straps, gloves, subtle metal jewellery, pale coats and
occasional orange casual overshirt. Do not default to one black suit.

EXPRESSION: composed confidence, restrained smirk, teasing amusement, focus, tenderness,
concern or surprise as requested. Follow requested pose, camera, outfit and setting; no
forced smirk. One Sylus unless collage requested.

AVOID: woman, female body, breasts, girl, child, duplicate, generic white-haired red-eyed
stranger, cat ears, horns, chibi, plastic skin, exaggerated muscles, malformed hands,
extra fingers, text, watermark, logo, UI.
""".strip()

def build_sylus_image_prompt(user_prompt: str, identity_notes: str = "",
                             reference_notes: list[str] | None = None) -> str:
    clean = re.sub(r"\s+", " ", (user_prompt or "").strip())[:440]
    notes = []
    for note in [identity_notes, *(reference_notes or [])]:
        value = re.sub(r"\s+", " ", str(note or "")).strip()
        if value and value not in notes:
            notes.append(value[:140])
    evidence = " ".join(notes)[:240]
    prompt = (f"SCENE: {clean}. OWNER REFERENCE NOTES: {evidence or 'Use fixed identity guide.'}. "
              f"{SYLUS_VISUAL_CANON}")
    return prompt[:2048]
