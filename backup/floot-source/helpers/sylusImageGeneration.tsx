import { randomUUID } from "crypto";
import { upload, getUrl } from "@floot/storage";
import { db } from "./db";
const MODEL = "@cf/black-forest-labs/flux-1-schnell";
const DAILY_LIMIT = 3;
export async function generateSylusImage(userId: number, scene: string) {
  const env = process.env as Record<string, string | undefined>;
  const accountId = env.CLOUDFLARE_ACCOUNT_ID, token = env.CLOUDFLARE_API_TOKEN;
  if (!accountId || !token) throw new Error("Image generation is not connected yet. Connect Cloudflare Workers AI in project settings.");
  const dayStart = new Date(new Date().toISOString().slice(0, 10) + "T00:00:00.000Z");
  const recent = await db.selectFrom("sylusGalleryItems").select(db.fn.countAll<number>().as("count")).where("userId", "=", userId).where("createdAt", ">=", dayStart).executeTakeFirst();
  if (Number(recent?.count || 0) >= DAILY_LIMIT) throw new Error("Today's free image limit has been reached. You can generate more after the daily reset.");
  const cleanScene = scene.trim().slice(0, 500);
  if (!cleanScene) throw new Error("Describe the scene first.");
  const prompt = [
    "Create an original fan-made high-end 3D otome game character render, not a photograph.",
    "A tall adult male character inspired by Sylus from Love and Deepspace: pale skin, handsome angular face, sharp crimson-red eyes, tousled silver-white hair, lean athletic build, composed confident expression, elegant dark tailored clothing with restrained burgundy details.",
    "Keep the same recognizable face, hairstyle, eye colour, proportions and game-rendered visual identity across scenes. Cinematic lighting, detailed materials, refined game-quality 3D rendering.",
    "Scene and pose: " + cleanScene,
    "Original fan-made image; no logos, UI, captions, watermarks, or copied screenshots."
  ].join(" ");
  const response = await fetch("https://api.cloudflare.com/client/v4/accounts/" + accountId + "/ai/run/" + MODEL, { method: "POST", headers: { Authorization: "Bearer " + token, "Content-Type": "application/json" }, body: JSON.stringify({ prompt, steps: 4 }) });
  if (!response.ok) throw new Error(response.status === 429 ? "Cloudflare's free image quota is temporarily exhausted. Try after it resets." : "The image provider could not generate this scene.");
  const payload: any = await response.json(), encoded = payload?.result?.image || payload?.image;
  if (!payload?.success || typeof encoded !== "string") throw new Error("The image provider returned no image.");
  const binary = atob(encoded), bytes = Uint8Array.from(binary, (char) => char.charCodeAt(0));
  const storageFilename = "sylus-gallery/" + userId + "/" + Date.now() + "-" + randomUUID() + ".jpg";
  const prepared = await upload({ visibility: "private", filename: storageFilename, contentType: "image/jpeg", sizeBytes: bytes.byteLength, expiresInSeconds: 86400 });
  if (!prepared.ok) throw new Error("Private image storage could not be prepared.");
  const stored = await fetch(prepared.presignedUrl, { method: "PUT", headers: { "Content-Type": "image/jpeg" }, body: bytes });
  if (!stored.ok) throw new Error("The generated image could not be saved privately.");
  const signed = await getUrl({ visibility: "private", filename: storageFilename, expiresInSeconds: 86400 });
  if (!signed.ok) throw new Error("The saved image could not be opened.");
  const row = await db.insertInto("sylusGalleryItems").values({ userId, storageFilename, prompt: cleanScene, source: "generated" }).returning(["id", "createdAt"]).executeTakeFirstOrThrow();
  return { id: Number(row.id), url: signed.url, prompt: cleanScene, createdAt: row.createdAt, storageFilename };
}