"""Sylus visual prompt builder. FLUX.1-schnell is text-to-image; private
reference photos contribute their saved text descriptions, not pixel conditioning."""
import re

SYLUS_VISUAL_CANON = """
SUBJECT: Sylus from Love and Deepspace. One unmistakably ADULT MASCULINE man; tall,
lean-athletic, mature natural male anatomy. Refined slightly long oval face, defined
cheekbones, tapered firm jaw/chin, straight narrow nose, defined lips, strong angled
silver brows. Never female, feminine, childlike, or a generic model.

EYES: narrow elongated almond shape; vivid deep crimson irises, dark pupils, subtle
darker limbal ring. His RIGHT eye is linked to the Aether Core; restrained red glow
there only when power is active. No giant neon eyes.

HAIR: cool silver-white/platinum, never blond. Dense layered feathered tousled cut:
lifted textured crown, distinct tapered locks, long side-swept fringe crossing forehead
and sometimes veiling one eye, shorter temple/ear layers, slightly longer nape. Fine
separated strands, flyaways, cool highlights/shadows. Keep this silhouette; no bob,
buzz cut, long flowing hair or smooth helmet.

RENDER: fair cool-neutral skin, subtle warmth, natural pores, soft subsurface scattering;
premium realistic 3D game-render, believable anatomy/materials. Not a real actor, chibi
or flat 2D anime.

CLOTHES: vary to match request: fitted black shirts/trousers; tailored black, charcoal,
slate-blue or burgundy suits; long dark coats; black/burgundy leather jackets; white/ivory
open-collar shirts, waistcoats, dark knitwear, high collars, restrained straps, gloves,
subtle metal jewellery. Pale coats/ivory knitwear and occasional orange casual overshirt
are also valid. Do not default to one black suit.

EXPRESSION: composed confidence, restrained smirk, teasing amusement, focus, tenderness,
concern or surprise as requested. Follow requested pose, camera, outfit and setting.
Do not force a smirk. One Sylus unless a collage is requested.

AVOID: woman, female body, breasts, girl, child, duplicate, generic white-haired red-eyed
stranger, cat ears, horns, chibi, plastic skin, exaggerated muscles, malformed hands,
extra fingers, text, watermark, logo, UI.
""".strip()

def build_sylus_image_prompt(user_prompt: str, identity_notes: str = "",
                             reference_notes: list[str] | None = None) -> str:
    clean = re.sub(r"\s+", " ", (user_prompt or "").strip())
    notes = []
    for note in [identity_notes, *(reference_notes or [])]:
        value = re.sub(r"\s+", " ", str(note or "")).strip()
        if value and value not in notes:
            notes.append(value[:180])
    evidence = " ".join(notes)[:220]
    prompt = (f"SCENE: {clean}. OWNER REFERENCE NOTES: {evidence or 'Use fixed identity guide.'}. "
              f"{SYLUS_VISUAL_CANON}")
    return prompt[:2048]
