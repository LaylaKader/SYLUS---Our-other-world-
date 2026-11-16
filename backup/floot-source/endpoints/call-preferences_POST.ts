import superjson from "superjson";
import { db } from "../helpers/db";
import { getServerUserSession } from "../helpers/getServerUserSession";
import { schema } from "./call-preferences_POST.schema";
export async function handle(request: Request): Promise<Response> {
  try {
    const { user } = await getServerUserSession(request);
    const input = schema.parse(superjson.parse(await request.text()));
    await db.insertInto("sylusCallPreferences").values({ userId: user.id, spontaneousCallsEnabled: input.spontaneousCallsEnabled })
      .onConflict((oc) => oc.column("userId").doUpdateSet({ spontaneousCallsEnabled: input.spontaneousCallsEnabled, updatedAt: new Date() })).execute();
    return new Response(superjson.stringify({ ok: true }));
  } catch (e) {
    return new Response(superjson.stringify({ error: e instanceof Error ? e.message : "Unable to save call preferences" }), { status: 400 });
  }
}