import superjson from "superjson";
import { getUrl } from "@floot/storage";
import { db } from "../../helpers/db";
import { getServerUserSession } from "../../helpers/getServerUserSession";
export async function handle(request: Request): Promise<Response> {
  try {
    const { user } = await getServerUserSession(request);
    const rows = await db.selectFrom("sylusGalleryItems").select(["id","storageFilename","prompt","createdAt"])
      .where("userId","=",user.id).orderBy("createdAt","desc").limit(100).execute();
    const images = [];
    for (const row of rows) {
      const signed = await getUrl({visibility:"private",filename:row.storageFilename,expiresInSeconds:86400});
      if (signed.ok) images.push({id:Number(row.id),url:signed.url,prompt:row.prompt,createdAt:row.createdAt});
    }
    return new Response(superjson.stringify({images}));
  } catch (e) {
    return new Response(superjson.stringify({error:e instanceof Error?e.message:"Unable to load gallery"}),{status:401});
  }
}