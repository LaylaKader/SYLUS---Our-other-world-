import superjson from "superjson";
export type OutputType = { preferences: { spontaneousCallsEnabled: boolean; noCallUntil: Date | null; noCallReason: string | null } };
export const getCallPreferences = async (): Promise<OutputType> => {
  const r = await fetch("/_api/call-preferences");
  if (!r.ok) throw new Error("Could not load call preferences");
  return superjson.parse<OutputType>(await r.text());
};