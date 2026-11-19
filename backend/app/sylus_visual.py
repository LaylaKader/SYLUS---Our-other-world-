"""Sylus prompt builder. FLUX.1-schnell is text-to-image; reference photos
are represented by saved text notes, not image-conditioning inputs."""
import re

SYLUS_VISUAL_CANON = """
Sylus (Love and Deepspace): ONE adult masculine man, tall, lean-athletic, mature male
anatomy. Refined slightly long face, defined cheekbones, tapered jaw, straight narrow
nose, defined lips, strong angled silver brows. Mature masculine facial proportions.
He is clean-shaven: completely smooth cheeks, jaw, chin and upper lip, with NO beard,
NO moustache, NO stubble and NO sideburn growth. Keep the jawline visible and unobscured.
Never female, feminized, childlike or facially aged.

EYES: narrow elongated almond eyes; vivid deep crimson irises, dark pupils, subtle limbal
rings. RIGHT eye links to the Aether Core; restrained red glow there only when active.

HAIR: cool silver-white/platinum, never blond. Dense layered feathered tousled cut:
lifted textured crown, separated tapered locks, long side-swept fringe across forehead
(sometimes over one eye), shorter temple layers, slightly longer nape. Fine individual
strand groups and delicate flyaways. Keep the recognizable silhouette; no bob, buzz cut
or long flowing hair.

RENDER: fair cool-neutral skin, natural smooth skin texture, premium realistic 3D game
render matching Love and Deepspace character-render aesthetics; believable adult male
anatomy. Not actor-photo, chibi or flat 2D anime.

WARDROBE: follow the user's request and vary tailored dark suits, fitted black shirts,
long dark coats, black/burgundy leather, white/ivory open-collar shirts, waistcoats,
dark knitwear, high collars, restrained straps, gloves, subtle jewellery, pale coats
or orange casual overshirt. Do not default to one black suit.

EXPRESSION: composed confidence, teasing smirk, focus, tenderness, concern or surprise
as requested. Follow requested pose, camera, outfit and setting; no forced smirk.
One Sylus unless collage requested.

AVOID: beard, bearded face, moustache, mustache, stubble, facial hair, five-o'clock
shadow, sideburns, woman, female body, breasts, girl, child, duplicate, generic
white-haired red-eyed stranger, cat ears, horns, chibi, plastic skin, malformed hands,
extra fingers, text, watermark, logo, UI.
""".strip()


def build_sylus_image_prompt(user_prompt: str, identity_notes: str = "",
                             reference_notes: list[str] | None = None) -> str:
    clean = re.sub(r"\s+", " ", (user_prompt or "").strip())[:220]
    notes = []
    for note in [identity_notes, *(reference_notes or [])]:
        value = re.sub(r"\s+", " ", str(note or "")).strip()
        if value and value not in notes:
            notes.append(value[:70])
    evidence = " ".join(notes)[:120]
    return (f"SCENE: {clean}. OWNER REFERENCE NOTES: {evidence or 'Use fixed identity guide.'}. "
            f"{SYLUS_VISUAL_CANON}")[:2048]
