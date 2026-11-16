import superjson from "superjson";
export type OutputType = { reactions: Array<{ messageId: number; emoji: string; actor: string }>; pinnedMessageIds: number[]; sylusPinnedMessageIds: number[] };
export const getMessageActions = async (): Promise<OutputType> => {
  const r = await fetch("/_api/message-actions");
  if (!r.ok) throw new Error("Could not load message actions");
  return superjson.parse<OutputType>(await r.text());
};