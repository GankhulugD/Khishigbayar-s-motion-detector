import { NextResponse } from "next/server";
import { cloudEnabled, cloudLive } from "@/lib/server/cloud";
import { activeDeviceId, buildSnapshot } from "@/lib/server/pipeline";
import { ensureSimulator } from "@/lib/server/simulator";
import { getRepository } from "@/lib/server/store";

export const dynamic = "force-dynamic";

/**
 * GET /api/live?device=<id>&since=<t>
 * Үүлэн (Vercel) горимд вэб ≈0.5 сек тутам асууна: хураангуй төлөв + since-ээс хойших хэмжилтүүд.
 * Локал горимд ч ажилладаг (SSE-ийн нөөц хувилбар).
 */
export async function GET(req: Request) {
  const url = new URL(req.url);
  const device = url.searchParams.get("device");
  const since = Number(url.searchParams.get("since") ?? 0) || 0;
  if (cloudEnabled) {
    return NextResponse.json(await cloudLive(device, since), { headers: { "cache-control": "no-store" } });
  }
  ensureSimulator();
  const id = device ?? activeDeviceId();
  const samples = id ? getRepository().getWindow(id, 8000).filter((s) => s.t > since) : [];
  return NextResponse.json({ deviceId: id, snap: buildSnapshot(id), samples }, { headers: { "cache-control": "no-store" } });
}
