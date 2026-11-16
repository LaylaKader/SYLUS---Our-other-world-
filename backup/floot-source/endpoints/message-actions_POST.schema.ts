import { z } from "zod";
import superjson from "superjson";
export const schema = z.object({ action: z.enum(["toggle_reaction", "toggle_pin"]), messageId: z.number().int().positive(), emoji: z.enum(["❤️", "😍", "🥰", "😂", "✨", "👍"]).optional() });
export type InputType = z.infer<typeof schema>;
export const postMessageActions = async (body: InputType) => {
  const r = await fetch("/_api/message-actions", { method: "POST", headers: { "Content-Type": "application/json" }, body: superjson.stringify(schema.parse(body)) });
  if (!r.ok) throw new Error("Could not update this message");
  return superjson.parse<{ ok: true }>(await r.text());
};