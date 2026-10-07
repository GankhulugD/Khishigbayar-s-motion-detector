import { NextResponse } from "next/server";
import { ingest, toDeviceResponse } from "@/lib/server/pipeline";
import type { IngestPayload } from "@/lib/types";

export const dynamic = "force-dynamic";

/**
 * ESP32-S3 → сервер.
 * Толгой: x-device-key: <DEVICE_API_KEY>
 * Бие:   { deviceId, samples: [{t,ax,ay,az,gx,gy,gz}], gps?: {lat,lng,accuracy}, battery?, rssi? }
 * Хариу: { ok, activity, label, confidence, alert }  ← төхөөрөмж OLED / buzzer-т ашиглана
 */
export async function POST(req: Request) {
  const key = process.env.DEVICE_API_KEY;
  if (key && req.headers.get("x-device-key") !== key) {
    return NextResponse.json({ ok: false, error: "unauthorized" }, { status: 401 });
  }

  let body: IngestPayload;
  try {
    body = (await req.json()) as IngestPayload;
  } catch {
    return NextResponse.json({ ok: false, error: "invalid json" }, { status: 400 });
  }
  if (!body?.deviceId || !Array.isArray(body.samples) || body.samples.length === 0) {
    return NextResponse.json({ ok: false, error: "deviceId, samples[] шаардлагатай" }, { status: 400 });
  }
  if (body.samples.length > 500) {
    return NextResponse.json({ ok: false, error: "нэг удаад 500-аас ихгүй хэмжилт" }, { status: 413 });
  }

  // Төхөөрөмжийн цаг тохируулаагүй (millis()) байж болох тул серверийн цагт шилжүүлнэ
  const now = Date.now();
  const last = body.samples[body.samples.length - 1].t;
  const offset = Math.abs(now - last) > 60_000 ? now - last : 0;
  const samples = body.samples.map((s) => ({ ...s, t: s.t + offset }));

  const pred = await ingest({ ...body, samples });
  return NextResponse.json(toDeviceResponse(pred));
}
