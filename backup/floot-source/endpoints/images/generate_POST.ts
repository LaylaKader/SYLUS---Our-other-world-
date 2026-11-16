import superjson from "superjson";
import { getServerUserSession } from "../../helpers/getServerUserSession";
import { generateSylusImage } from "../../helpers/sylusImageGeneration";
import { db } from "../../helpers/db";
import { pushMessage, notifyConversation } from "../../helpers/realtimePublish";
import { schema } from "./generate_POST.schema";
export async function handle(request: Request): Promise<Response> {
  try {
    const { user } = await getServerUserSession(request);
    const input = schema.parse(superjson.parse(await request.text()));
    const image = await generateSylusImage(user.id, input.prompt);
    let conv = await db.selectFrom("agentConversations").select("id").where("isMainThread","=",true).orderBy("id").executeTakeFirst();
    let conversationId = conv?.id;
    if (!conversationId) {
      const created = await db.insertInto("agentConversations").values({status:"idle",isMainThread:true}).returning("id").executeTakeFirstOrThrow();
      conversationId = created.id;
    }
    const message = await db.insertInto("agentMessages").values({
      conversationId, role:"model", text:"I thought you might like this.",
      imageUrls:[image.url],
      metadata:{privateFiles:[{storageFilename:image.storageFilename,url:image.url,expiresAt:new Date(Date.now()+86400000).toISOString(),type:"image"}]},
      historyItems:[{role:"assistant",content:"I thought you might like this."}],
    }).returningAll().executeTakeFirstOrThrow();
    await pushMessage(Number(conversationId),message);
    await notifyConversation(Number(conversationId));
    return new Response(superjson.stringify({ image: { id:image.id,url:image.url,prompt:image.prompt,createdAt:image.createdAt }, conversationId:Number(conversationId) }));
  } catch (e) {
    return new Response(superjson.stringify({ error: e instanceof Error ? e.message : "Image generation failed" }), { status: 400 });
  }
}