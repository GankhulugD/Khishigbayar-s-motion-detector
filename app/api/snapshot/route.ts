import { NextResponse } from "next/server";
import { activeDeviceId, buildSnapshot, toDeviceResponse } from "@/lib/server/pipeline";
import { ensureSimulator } from "@/lib/server/simulator";
import { getRepository } from "@/lib/server/store";

export const dynamic = "force-dynamic";

/**
 * GET /api/snapshot                → веб самбарын бүрэн төлөв
 * GET /api/snapshot?device=<id>&compact=1 → төхөөрөмж сүүлийн үр дүнг татах (OLED)
 */
export async function GET(req: Request) {
  ensureSimulator();
  const url = new URL(req.url);
  const device = url.searchParams.get("device") ?? activeDeviceId();
  if (url.searchParams.get("compact")) {
    const pred = device ? getRepository().latestPrediction(device) : null;
    return NextResponse.json(toDeviceResponse(pred));
  }
  return NextResponse.json(buildSnapshot(device));
}
