import { NextResponse } from "next/server";
import { activeDeviceId, startOfToday } from "@/lib/server/pipeline";
import { ensureSimulator } from "@/lib/server/simulator";
import { getRepository } from "@/lib/server/store";

export const dynamic = "force-dynamic";

/** GET /api/history?device=<id> → өнөөдрийн цаг тутмын хуваарилалт ба хэсгүүд */
export async function GET(req: Request) {
  ensureSimulator();
  const url = new URL(req.url);
  const device = url.searchParams.get("device") ?? activeDeviceId();
  if (!device) return NextResponse.json({ hours: [], segments: [] });
  const repo = getRepository();
  const day = startOfToday();
  const now = Date.now();
  const hours = Array.from({ length: 24 }, (_, h) => {
    const a = day + h * 3600_000;
    return { hour: h, durations: a > now ? null : repo.durations(device, a, Math.min(a + 3600_000, now)) };
  });
  return NextResponse.json({ deviceId: device, hours, segments: repo.segments(device, day), alerts: repo.alerts(device, 50) });
}
