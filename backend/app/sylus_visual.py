"""Stable character prompting for Sylus. FLUX.1-schnell is text-to-image:
reference photos are summarized as text, not supplied as image-conditioning inputs."""
import re

SYLUS_VISUAL_CANON = """
IDENTITY LOCK: Sylus from Love and Deepspace; one unmistakably adult, tall, lean-athletic
MAN with mature masculine anatomy, broad natural shoulders, defined neck, long refined
face, high cheekbones, tapered firm jaw and chin, straight narrow nose, defined lips,
strong slightly angled silver brows. Never female, feminine, childlike, or a generic model.

FACE AND EYES: balanced mature masculine facial proportions; narrow elongated almond eyes,
vivid deep crimson irises with dark pupils and subtle darker limbal rings. His RIGHT eye
is associated with the Aether Core; only show a restrained red glow there when the scene
calls for active power. Do not turn the eyes into oversized neon discs.

HAIR: signature cool silver-white/platinum, not blond or paper-white. Dense layered,
feathered, tousled cut: lifted airy crown, distinct tapered locks, long side-swept fringe
crossing the forehead and sometimes veiling one eye, shorter temple/ear layers, slightly
longer nape pieces. Fine separated strand groups, flyaways, cool highlights and shadows.
Keep this silhouette; no bob, buzz cut, long flowing hair, smooth helmet or random spikes.

SKIN/RENDER: fair cool-neutral skin with subtle warmth, natural pores and soft subsurface
scattering. Premium realistic 3D game-render aesthetic, believable anatomy and materials;
not a real actor, not chibi, not flat 2D anime.

WARDROBE: vary according to the request. His established style includes fitted black
shirts/trousers, black or burgundy leather jackets, long charcoal/black/dark-brown coats,
tailored black/charcoal/slate-blue/burgundy suits, white or ivory open-collar shirts,
waistcoats, layered shirts, dark knitwear, high collars, restrained straps/harness details,
gloves and understated metal jewellery. Casual orange overshirt over a graphic tee is
also valid. Pale tailored coats and soft ivory knitwear are valid. Do not force one outfit.

EXPRESSION/POSE: composed confidence, restrained smirk, teasing amusement, focused
intensity, quiet tenderness, concern or genuine surprise as requested. Follow the exact
requested pose, camera angle, setting, clothing and expression; do not smirk every time.
One Sylus only unless a collage is explicitly requested.

NEGATIVE: woman, female body, breasts, girl, child, duplicate person, extra face, generic
white-haired red-eyed stranger, cat ears, horns, chibi, plastic skin, exaggerated muscles,
malformed hands, extra fingers, text, watermark, logo, UI.
""".strip()

def build_sylus_image_prompt(user_prompt: str, identity_notes: str = "",
                             reference_notes: list[str] | None = None) -> str:
    clean = re.sub(r"\s+", " ", (user_prompt or "").strip())
    notes = []
    for note in [identity_notes, *(reference_notes or [])]:
        value = re.sub(r"\s+", " ", str(note or "")).strip()
        if value and value not in notes:
            notes.append(value[:260])
    evidence = " ".join(notes)[:430]
    # Keep user intent and anti-gender-drift constraints ahead of optional detail.
    prompt = (f"SCENE: {clean}. OWNER-APPROVED REFERENCE NOTES: {evidence or 'Use the fixed design below.'}. "
              f"{SYLUS_VISUAL_CANON}")
    return prompt[:2048]
