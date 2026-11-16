import superjson from "superjson";
import { db } from "../helpers/db";
import { getServerUserSession } from "../helpers/getServerUserSession";
export async function handle(request: Request): Promise<Response> {
  try {
    const { user } = await getServerUserSession(request);
    const reactions = await db.selectFrom("sylusMessageReactions").select(["messageId", "emoji", "actor"]).where("userId", "=", user.id).execute();
    const pins = await db.selectFrom("sylusPinnedMessages").select(["messageId", "actor"]).where("userId", "=", user.id).orderBy("createdAt", "desc").execute();
    return new Response(superjson.stringify({ reactions: reactions.map(r => ({ messageId: Number(r.messageId), emoji: r.emoji, actor: r.actor })), pinnedMessageIds: pins.filter(p=>p.actor==="user").map(p => Number(p.messageId)), sylusPinnedMessageIds: pins.filter(p=>p.actor==="sylus").map(p => Number(p.messageId)) }));
  } catch (e) {
    return new Response(superjson.stringify({ error: e instanceof Error ? e.message : "Unable to load message actions" }), { status: 401 });
  }
}