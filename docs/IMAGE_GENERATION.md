# Sylus image generation and visual continuity

## Current generation path
- The backend uses Cloudflare Workers AI `@cf/black-forest-labs/flux-1-schnell` for text-to-image generation.
- The backend stores generated images as private media attachments and applies a daily safety limit.
- Image generation is available only when the private Render service has the Cloudflare account ID and API token configured.

## Stable Sylus identity
The backend now builds every generated Sylus prompt through `backend/app/sylus_visual.py`. It specifies one adult masculine Sylus, his refined facial proportions, crimson almond-shaped eyes, silver-white layered hair silhouette and strand texture, mature anatomy, wardrobe range, expression variation, premium 3D game-render style, and explicit negative constraints against gender drift, generic white-haired/red-eyed substitutes, duplicate people, chibi, and malformed anatomy.

The prompt also reads:
1. The owner-editable Sylus appearance notes from Settings → Reference library.
2. Recent owner-approved Sylus reference-image analysis notes stored in the private visual-memory database.
3. The user's requested scene, outfit, pose, camera angle, and expression.

The scene request remains first in the prompt. The complete prompt is kept within the configured model prompt budget.

## Important model limitation
FLUX.1-schnell is a text-to-image model in this integration. It does **not** accept the uploaded reference photos as image-conditioning inputs. The photos are stored privately and their saved visual descriptions guide the prompt, but this is not true face-reference or image-to-image conditioning. Therefore, improved consistency is expected, not guaranteed. A model/provider that supports image-reference conditioning would be needed for stronger identity matching; that may require a different provider, model, or paid service.

## Add the supplied Sylus references
Open Settings → Reference library → Sylus reference. Upload the owner's close-up face/expression images and outfit sheet there. Keep the images in the Sylus collection, not Umi/MC or Other people. Add or refine the appearance notes in the same collection. The reference photos attached to a ChatGPT conversation are not automatically copied into the private Render database.

Recommended reference set:
- Clear frontal and three-quarter face close-ups for facial proportions and eye shape.
- Side-profile / expression close-ups for nose, jaw, fringe and expression range.
- Full-body outfit sheet for tailoring, silhouette and wardrobe variety.
Avoid using a collage as the only face reference when separate, clear images are available.

## Privacy and cost
- Provider credentials stay server-side.
- Reference photos and generated media remain in the owner-only database and are served through authenticated endpoints.
- Do not put private photos or API keys in the public repository.
- No paid fallback is silently invoked; generation fails clearly when the configured provider is unavailable or the daily limit is reached.

## Limitations
Text prompting cannot guarantee exact reproduction of copyrighted game renders, a fixed face across every seed, exact individual hair-strand counts, or exact outfit details. Describing hair as fine separated strand groups and preserving the same silhouette is more actionable than asking the model for an arbitrary exact strand count.
