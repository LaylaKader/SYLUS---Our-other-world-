import { z } from "zod";
import superjson from "superjson";
export const schema = z.object({ prompt: z.string().min(3).max(500) });
export type InputType = z.infer<typeof schema>;
export type OutputType = { image: { id: number; url: string; prompt: string; createdAt: Date } };
export const postImageGenerate = async (body: InputType): Promise<OutputType> => {
  const r = await fetch("/_api/images/generate", { method: "POST", headers: { "Content-Type": "application/json" }, body: superjson.stringify(schema.parse(body)) });
  if (!r.ok) throw new Error(superjson.parse<{error:string}>(await r.text()).error);
  return superjson.parse<OutputType>(await r.text());
};