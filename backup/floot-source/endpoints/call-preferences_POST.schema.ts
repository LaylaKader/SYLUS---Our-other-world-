import { z } from "zod";
import superjson from "superjson";
export const schema = z.object({ spontaneousCallsEnabled: z.boolean() });
export type InputType = z.infer<typeof schema>;
export const postCallPreferences = async (body: InputType) => {
  const r = await fetch("/_api/call-preferences", { method: "POST", headers: { "Content-Type": "application/json" }, body: superjson.stringify(schema.parse(body)) });
  if (!r.ok) throw new Error("Could not save call preferences");
  return superjson.parse<{ ok: true }>(await r.text());
};