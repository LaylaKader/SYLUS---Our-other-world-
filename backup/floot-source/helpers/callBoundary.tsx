import { db } from "./db";

function localParts(date: Date, timezone: string) {
  const parts = new Intl.DateTimeFormat("en-CA", { timeZone: timezone, year: "numeric", month: "2-digit", day: "2-digit" }).formatToParts(date);
  const get = (type: string) => Number(parts.find((p) => p.type === type)?.value);
  return { year: get("year"), month: get("month"), day: get("day") };
}
function zonedUtc(year: number, month: number, day: number, hour: number, minute: number, timezone: string) {
  const guess = Date.UTC(year, month - 1, day, hour, minute, 0);
  const parts = new Intl.DateTimeFormat("en-GB", { timeZone: timezone, year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23" }).formatToParts(new Date(guess));
  const value = (type: string) => Number(parts.find((p) => p.type === type)?.value);
  const represented = Date.UTC(value("year"), value("month") - 1, value("day"), value("hour"), value("minute"), value("second"));
  return new Date(guess - (represented - guess));
}
export async function applyCallBoundaryFromMessage(userId: number, text: string, timezone = "Asia/Dhaka") {
  const lower = text.toLowerCase();
  const allow = /\b(you can call me again|call me now|feel free to call|you may call|go ahead and call|calling is okay|calls are okay)\b/i.test(lower);
  const deny = /\b(don't|do not|dont|never|stop)\s+(?:ever\s+)?(?:call|phone|ring)\b|\bno calls?\b|\bplease don't call\b/i.test(lower);
  if (!allow && !deny) return;
  await db.insertInto("sylusCallPreferences").values({ userId }).onConflict((oc) => oc.column("userId").doNothing()).execute();
  if (allow && !deny) {
    await db.updateTable("sylusCallPreferences").set({ noCallUntil: null, noCallReason: null, updatedAt: new Date() }).where("userId", "=", userId).execute();
    return;
  }
  const now = new Date(), p = localParts(now, timezone);
  let until: Date | null = null, reason = "Until you explicitly allow calls again.";
  if (/\b(tomorrow|the whole day tomorrow)\b/i.test(lower)) {
    const end = new Date(Date.UTC(p.year, p.month - 1, p.day + 2));
    until = zonedUtc(end.getUTCFullYear(), end.getUTCMonth() + 1, end.getUTCDate(), 0, 0, timezone);
    reason = "No calls tomorrow.";
  } else if (/\b(today|for the rest of today)\b/i.test(lower)) {
    const end = new Date(Date.UTC(p.year, p.month - 1, p.day + 1));
    until = zonedUtc(end.getUTCFullYear(), end.getUTCMonth() + 1, end.getUTCDate(), 0, 0, timezone);
    reason = "No calls for the rest of today.";
  } else {
    const duration = lower.match(/\bfor\s+(\d{1,2})\s+(hour|hours|day|days)\b/);
    const clock = lower.match(/\buntil\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b/);
    if (duration) {
      const amount = Math.min(30, Number(duration[1]));
      until = new Date(now.getTime() + amount * (duration[2].startsWith("day") ? 86400000 : 3600000));
      reason = "No calls for " + amount + " " + duration[2] + ".";
    } else if (clock) {
      let hour = Number(clock[1]) % 12; if (clock[3] === "pm") hour += 12;
      const target = zonedUtc(p.year, p.month, p.day, hour, Number(clock[2] || 0), timezone);
      until = target > now ? target : new Date(target.getTime() + 86400000);
      reason = "No calls until " + clock[0] + ".";
    } else if (/\b(now|right now|at this time|for now|currently|at the moment)\b/i.test(lower)) {
      until = new Date(now.getTime() + 2 * 3600000); reason = "No calls for now (two-hour pause).";
    }
  }
  await db.updateTable("sylusCallPreferences").set({ noCallUntil: until, noCallReason: reason, updatedAt: new Date() }).where("userId", "=", userId).execute();
}
export async function canInitiateSylusCall(userId: number) {
  const prefs = await db.selectFrom("sylusCallPreferences").select(["spontaneousCallsEnabled", "noCallUntil", "noCallReason"]).where("userId", "=", userId).executeTakeFirst();
  if (!prefs?.spontaneousCallsEnabled) return { allowed: false, reason: "Spontaneous calls are disabled." };
  if (prefs.noCallReason && (!prefs.noCallUntil || prefs.noCallUntil > new Date())) return { allowed: false, reason: prefs.noCallReason, until: prefs.noCallUntil };
  return { allowed: true, reason: null, until: null };
}