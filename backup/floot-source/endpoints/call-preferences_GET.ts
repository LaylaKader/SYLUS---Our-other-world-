import superjson from "superjson";
import { db } from "../helpers/db";
import { getServerUserSession } from "../helpers/getServerUserSession";
export async function handle(request: Request): Promise<Response> {
  try {
    const { user } = await getServerUserSession(request);
    await db.insertInto("sylusCallPreferences").values({ userId: user.id }).onConflict((oc) => oc.column("userId").doNothing()).execute();
    let preferences = await db.selectFrom("sylusCallPreferences").select(["spontaneousCallsEnabled", "noCallUntil", "noCallReason"]).where("userId", "=", user.id).executeTakeFirstOrThrow();
    if (preferences.noCallUntil && preferences.noCallUntil <= new Date()) {
      await db.updateTable("sylusCallPreferences").set({ noCallUntil: null, noCallReason: null, updatedAt: new Date() }).where("userId", "=", user.id).execute();
      preferences = { ...preferences, noCallUntil: null, noCallReason: null };
    }
    return new Response(superjson.stringify({ preferences }));
  } catch (e) {
    return new Response(superjson.stringify({ error: e instanceof Error ? e.message : "Unable to load call preferences" }), { status: 401 });
  }
}