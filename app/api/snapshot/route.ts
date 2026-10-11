import { NextResponse } from "next/server";
import { activeDeviceId, buildSnapshot, toDeviceResponse } from "@/lib/server/pipeline";
import { ensureSimulator } from "@/lib/server/simulator";
import { getRepository } from "@/lib/server/store";
import { cloudEnabled, cloudLatest, cloudLive } from "@/lib/server/cloud";

export const dynamic = "force-dynamic";

/**
 * GET /api/snapshot                → веб самбарын бүрэн төлөв
 * GET /api/snapshot?device=<id>&compact=1 → төхөөрөмж сүүлийн үр дүнг татах (OLED)
 */
export async function GET(req: Request) {
  const url = new URL(req.url);
  if (cloudEnabled) {
    const dev = url.searchParams.get("device");
    if (url.searchParams.get("compact")) return NextResponse.json(await cloudLatest(dev));
    return NextResponse.json((await cloudLive(dev, Infinity)).snap);
  }
  ensureSimulator();
  const device = url.searchParams.get("device") ?? activeDeviceId();
  if (url.searchParams.get("compact")) {
    const pred = device ? getRepository().latestPrediction(device) : null;
    return NextResponse.json(toDeviceResponse(pred));
  }
  return NextResponse.json(buildSnapshot(device));
}
