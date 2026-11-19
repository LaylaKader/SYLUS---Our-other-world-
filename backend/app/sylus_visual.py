"""Stable Sylus visual prompting. FLUX.1-schnell is text-to-image: reference
photos are summarized as text, not passed as image-conditioning inputs."""
import re

SYLUS_VISUAL_CANON = """
IDENTITY: Sylus from Love and Deepspace; one unmistakably adult, tall, lean-athletic
MAN with mature masculine anatomy. Refined long-oval face, defined cheekbones, tapered
firm jaw and chin, straight narrow nose, defined lips, strong slightly angled silver brows.
Keep balanced, mature masculine proportions. Never feminize him or depict a woman/girl.

EYES: narrow elongated almond eyes, vivid deep crimson irises, dark pupils and subtle
darker limbal rings. His RIGHT eye is associated with the Aether Core; show a restrained
red glow there only when active power is relevant. No oversized neon eye discs.

HAIR: cool silver-white/platinum, not blond or paper-white. Dense, layered, feathered,
tousled cut; lifted airy crown, separated tapered locks, long side-swept fringe crossing
the forehead and sometimes veiling one eye, shorter temple/ear layers, slightly longer
nape pieces. Fine visible strand groups, flyaways, cool highlights/shadows. Preserve this
recognizable silhouette; no bob, buzz cut, long flowing hair or smooth helmet.

RENDER: fair cool-neutral skin with subtle warmth, natural pores and soft subsurface
scattering. Premium realistic 3D game-render aesthetic, natural anatomy/materials; not
a real actor, not chibi, not flat 2D anime.

WARDROBE: vary with the request. Tailored dark suits, fitted black shirts/trousers,
long charcoal/black/dark-brown coats, black or burgundy leather jackets, white/ivory
open-collar shirts, waistcoats, dark knitwear, high collars, restrained straps, gloves
and subtle metal jewellery. Pale coats/ivory knitwear and occasional orange casual
overshirt are also valid. Do not force the same black suit every time.

EXPRESSION: composed confidence, restrained smirk, teasing amusement, focus, tenderness,
concern or surprise as requested. Follow requested pose, camera, outfit and setting;
do not force a smirk. One Sylus only unless a collage is requested.

NEGATIVE: woman, female body, breasts, girl, child, duplicate, generic white-haired
red-eyed stranger, cat ears, horns, chibi, plastic skin, exaggerated muscles, malformed
hands, extra fingers, text, watermark, logo, UI.
""".strip()

def build_sylus_image_prompt(user_prompt: str, identity_notes: str = "",
                             reference_notes: list[str] | None = None) -> str:
    clean = re.sub(r"\s+", " ", (user_prompt or "").strip())
    notes = []
    for note in [identity_notes, *(reference_notes or [])]:
        value = re.sub(r"\s+", " ", str(note or "")).strip()
        if value and value not in notes:
            notes.append(value[:220])
    evidence = " ".join(notes)[:300]
    prompt = (f"SCENE: {clean}. OWNER REFERENCE NOTES: {evidence or 'Follow fixed identity guide.'}. "
              f"{SYLUS_VISUAL_CANON}")
    return prompt[:2048]
