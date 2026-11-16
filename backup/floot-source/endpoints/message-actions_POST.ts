import superjson from "superjson";
import { sql } from "../helpers/agentSql";
import { getServerUserSession } from "../helpers/getServerUserSession";
import { schema } from "./message-actions_POST.schema";
export async function handle(request: Request): Promise<Response> {
  try {
    const { user } = await getServerUserSession(request);
    const input = schema.parse(superjson.parse(await request.text()));
    const exists = await sql`SELECT id FROM agent_messages WHERE id = ${input.messageId} LIMIT 1`;
    if (!exists.length) return new Response(superjson.stringify({ error: "Message not found." }), { status: 404 });
    if (input.action === "toggle_reaction") {
      if (!input.emoji) return new Response(superjson.stringify({ error: "Choose a reaction." }), { status: 400 });
      const prior = await sql`SELECT id FROM sylus_message_reactions WHERE user_id = ${user.id} AND message_id = ${input.messageId} AND emoji = ${input.emoji} LIMIT 1`;
      if (prior.length) await sql`DELETE FROM sylus_message_reactions WHERE id = ${prior[0].id}`;
      else await sql`INSERT INTO sylus_message_reactions (user_id,message_id,emoji,actor) VALUES (${user.id},${input.messageId},${input.emoji},'user') ON CONFLICT (user_id,message_id,emoji,actor) DO NOTHING`;
    } else {
      const prior = await sql`SELECT id FROM sylus_pinned_messages WHERE user_id = ${user.id} AND message_id = ${input.messageId} LIMIT 1`;
      if (prior.length) await sql`DELETE FROM sylus_pinned_messages WHERE id = ${prior[0].id}`;
      else await sql`INSERT INTO sylus_pinned_messages (user_id,message_id,actor) VALUES (${user.id},${input.messageId},'user') ON CONFLICT (user_id,message_id,actor) DO NOTHING`;
    }
    return new Response(superjson.stringify({ ok: true }));
  } catch (e) {
    return new Response(superjson.stringify({ error: e instanceof Error ? e.message : "Unable to update message" }), { status: 400 });
  }
}