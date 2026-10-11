import { EventEmitter } from "node:events";
import { ACTIVITIES } from "../activities";
import type { DeviceResponse, IngestPayload, Prediction, Snapshot } from "../types";
import { createClassifier, type Classifier } from "./classifier";
import { getRepository, type MemoryRepository } from "./store";

/**
 * Өгөгдөл боловсруулах урсгал:
 * төхөөрөмж → ingest → хадгалах → цонх (2 сек) → ML ангилал → үр дүн → (төхөөрөмж, веб)
 */
const WINDOW_MS = 2000;
const OFFLINE_MS = 10_000;

const g = globalThis as unknown as { __bus?: EventEmitter; __clf?: Classifier; __lastFall?: Map<string, number> };
export const bus = (g.__bus ??= new EventEmitter().setMaxListeners(100));
const classifier = (g.__clf ??= createClassifier());
export const lastFall = (g.__lastFall ??= new Map<string, number>());

export async function ingest(
  p: IngestPayload,
  opts: { simulated?: boolean } = {},
  repo: MemoryRepository = getRepository(),
): Promise<Prediction | null> {
  const now = Date.now();
  repo.upsertDevice({
    deviceId: p.deviceId,
    online: true,
    lastSeen: now,
    battery: p.battery,
    rssi: p.rssi,
    ip: p.ip,
    simulated: opts.simulated ?? false,
    name: opts.simulated ? "Demo төхөөрөмж" : p.deviceId,
  });
  repo.addSamples(p.deviceId, p.samples);
  // Түүхий мэдрэгчийн өгөгдлийг веб рүү шууд дамжуулна (ангиллыг хүлээхгүй)
  bus.emit("samples", p.deviceId, p.samples);
  if (p.gps) repo.setGps(p.deviceId, { ...p.gps, t: p.gps.t ?? now });

  const pred = await classifier.predict(p.deviceId, repo.getWindow(p.deviceId, WINDOW_MS));
  if (!pred) return null;
  repo.addPrediction(pred);

  if (pred.activity === "fall" && now - (lastFall.get(p.deviceId) ?? 0) > 30_000) {
    lastFall.set(p.deviceId, now);
    repo.addAlert({
      deviceId: p.deviceId,
      t: now,
      kind: "fall",
      message: "Болзошгүй уналт илэрлээ",
      gps: repo.getGps(p.deviceId) ?? undefined,
    });
  }
  bus.emit("update", p.deviceId);
  return pred;
}

/** Төхөөрөмжийн OLED / buzzer-д буцаах товч хариу */
export function toDeviceResponse(pred: Prediction | null): DeviceResponse {
  return {
    ok: true,
    activity: pred?.activity ?? null,
    label: pred ? ACTIVITIES[pred.activity].short : null,
    confidence: pred ? Math.round(pred.confidence * 100) / 100 : null,
    alert: pred?.activity === "fall",
  };
}

/** Веб дээр харуулах төхөөрөмж: сүүлд идэвхтэй байсан бодит төхөөрөмж, байхгүй бол demo */
export function activeDeviceId(repo: MemoryRepository = getRepository()): string | null {
  const devices = repo.listDevices();
  if (!devices.length) return null;
  const real = devices.filter((d) => !d.simulated).sort((a, b) => b.lastSeen - a.lastSeen)[0];
  if (real && Date.now() - real.lastSeen < OFFLINE_MS) return real.deviceId;
  return devices.sort((a, b) => b.lastSeen - a.lastSeen)[0].deviceId;
}

export function startOfToday(now = Date.now()) {
  const d = new Date(now);
  d.setHours(0, 0, 0, 0);
  return d.getTime();
}

export function buildSnapshot(deviceId = activeDeviceId(), repo: MemoryRepository = getRepository()): Snapshot {
  const now = Date.now();
  if (!deviceId) {
    return { now, device: null, current: null, currentSince: null, signal: [], today: { sitting: 0, standing: 0, walking: 0, running: 0, lying: 0, fall: 0 }, timeline: [], alerts: [], gps: null };
  }
  const dev = repo.getDevice(deviceId)!;
  const device = { ...dev, online: now - dev.lastSeen < OFFLINE_MS };
  const since = startOfToday(now);
  const segments = repo.segments(deviceId, since);
  const last = segments[segments.length - 1];
  const raw = repo.getWindow(deviceId, 10_000);
  const step = Math.max(1, Math.floor(raw.length / 200));
  const signal = raw
    .filter((_, i) => i % step === 0)
    .map((s) => ({ t: s.t, mag: Math.hypot(s.ax, s.ay, s.az), ax: s.ax, ay: s.ay, az: s.az }));
  return {
    now,
    device,
    current: repo.latestPrediction(deviceId),
    currentSince: last ? last.start : null,
    signal,
    today: repo.durations(deviceId, since, now),
    timeline: segments.slice(-60),
    alerts: repo.alerts(deviceId, 10),
    gps: repo.getGps(deviceId),
  };
}
