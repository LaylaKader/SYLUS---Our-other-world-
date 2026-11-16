import superjson from "superjson";
export type OutputType = { images: Array<{id:number;url:string;prompt:string;createdAt:Date}> };
export const getSylusImages = async (): Promise<OutputType> => {
  const r=await fetch("/_api/images/list");
  if(!r.ok)throw new Error("Could not load the private gallery");
  return superjson.parse<OutputType>(await r.text());
};