import { Redis } from "@upstash/redis";
import { emptyDurations } from "../activities";
import type { Activity, Alert, DeviceResponse, DeviceStatus, GpsFix, IngestPayload, Prediction, SensorSample, Segment, Snapshot } from "../types";
import { alignClock, type DeviceClock } from "./clock";
import { buildSnapshot, ingest, lastFall, startOfToday, toDeviceResponse } from "./pipeline";
import { MemoryRepository } from "./store";

/**
 * Үүлэн горим (Vercel + Upstash Redis).
 *
 * Vercel-ийн функцууд хүсэлт бүрт шинээр (эсвэл өөр instance дээр) ажилладаг тул санах ойд
 * хадгалсан төлөв хуваалцагдахгүй. Иймд төхөөрөмж бүрийн "идэвхтэй төлөв"-ийг Redis-д нэг жижиг
 * JSON (blob) болгон хадгална:
 *   ingest  → GET blob → ангилал → SET blob            (2 команд)
 *   веб     → GET blob (≈0.5 сек тутам)                 (1 команд)
 * Хуучирсан хэсгүүд (segment) өдрийн жагсаалт руу (mc:segs:<id>:<өдөр>) шилжиж, нийлбэр нь carry-д үлдэнэ.
 *
 * Орчны хувьсагч: KV_REST_API_URL + KV_REST_API_TOKEN (Vercel Marketplace → Upstash)
 *                эсвэл UPSTASH_REDIS_REST_URL + UPSTASH_REDIS_REST_TOKEN
 */
const URL_ = process.env.KV_REST_API_URL ?? process.env.UPSTASH_REDIS_REST_URL;
const TOKEN = process.env.KV_REST_API_TOKEN ?? process.env.UPSTASH_REDIS_REST_TOKEN;
export const cloudEnabled = Boolean(URL_ && TOKEN);
const redis = cloudEnabled ? new Redis({ url: URL_!, token: TOKEN! }) : null;

const KEEP_SAMPLES_MS = 3_000; // ангиллын цонх 2 сек + нөөц
const KEEP_SEGMENTS = 60; // timeline-д харуулах тоо
const TTL = 7 * 24 * 3600; // сек
const ACTIVE_KEY = "mc:active";
const devKey = (id: string) => `mc:dev:${id}`;
const segKey = (id: string, day: number) => `mc:segs:${id}:${day}`;

type Packed = [number, number, number, number, number, number, number];
interface Blob {
  v: 1;
  device: DeviceStatus;
  samples: Packed[];
  pred: Prediction | null;
  segs: Segment[];
  /** Blob-оос гарсан (хуучин) хэсгүүдийн өнөөдрийн нийлбэр */
  carry: { day: number; totals: Record<Activity, number> };
  alerts: Alert[];
  alertSeq: number;
  gps: GpsFix | null;
  clock?: DeviceClock;
  lastFall?: number;
}

const pack = (s: SensorSample): Packed => [s.t, s.ax, s.ay, s.az, s.gx, s.gy, s.gz];
const unpack = ([t, ax, ay, az, gx, gy, gz]: Packed): SensorSample => ({ t, ax, ay, az, gx, gy, gz });

function load(blob: Blob | null): MemoryRepository {
  const repo = new MemoryRepository();
  if (blob) {
    repo.importDevice(
      blob.device,
      {
        samples: blob.samples.map(unpack),
        predictions: blob.pred ? [blob.pred] : [],
        segments: blob.segs,
        gps: blob.gps,
        alerts: blob.alerts,
      },
      blob.alertSeq,
    );
  }
  return repo;
}

function overlap(seg: Segment, a: number, b: number) {
  return Math.max(0, Math.min(seg.end, b) - Math.max(seg.start, a));
}

/** ESP32 → POST /api/ingest (үүлэн горим) */
export async function cloudIngest(body: IngestPayload): Promise<DeviceResponse> {
  const id = body.deviceId;
  const prev = await redis!.get<Blob>(devKey(id));
  const now = Date.now();
  const day = startOfToday(now);

  const { samples, clock } = alignClock(body.samples, prev?.clock, now);
  const repo = load(prev);
  if (prev?.lastFall) lastFall.set(id, prev.lastFall);
  const pred = await ingest({ ...body, samples }, {}, repo);

  const { device, state, alertSeq } = repo.exportDevice(id);
  const lastT = state.samples.length ? state.samples[state.samples.length - 1].t : now;

  // Хэт олон хэсэг хуримтлагдвал хуучныг өдрийн жагсаалт руу шилжүүлж, нийлбэрийг carry-д нэмнэ
  let carry = prev?.carry && prev.carry.day === day ? prev.carry : { day, totals: emptyDurations() };
  let segs = state.segments;
  const writes: Promise<unknown>[] = [];
  if (segs.length > KEEP_SEGMENTS + 20) {
    const old = segs.slice(0, segs.length - KEEP_SEGMENTS);
    segs = segs.slice(-KEEP_SEGMENTS);
    const totals = { ...carry.totals };
    for (const s of old) totals[s.activity] += overlap(s, day, day + 86_400_000);
    carry = { day, totals };
    const p = redis!.pipeline();
    p.rpush(segKey(id, day), ...old.map((s) => JSON.stringify(s)));
    p.expire(segKey(id, day), 3 * 86_400);
    writes.push(p.exec());
  }

  const blob: Blob = {
    v: 1,
    device: device!,
    samples: state.samples.filter((s) => s.t > lastT - KEEP_SAMPLES_MS).map(pack),
    pred: pred ?? prev?.pred ?? null,
    segs,
    carry,
    alerts: state.alerts.slice(0, 20),
    alertSeq,
    gps: state.gps,
    clock,
    lastFall: lastFall.get(id),
  };
  writes.push(redis!.set(devKey(id), blob, { ex: TTL }));
  // Шинэ эсвэл дахин холбогдсон төхөөрөмжийг "идэвхтэй" болгоно (байнга бичихгүй — командын тоо хэмнэнэ)
  if (!prev || now - prev.device.lastSeen > 10_000) writes.push(redis!.set(ACTIVE_KEY, id, { ex: TTL }));
  await Promise.all(writes);
  return toDeviceResponse(pred ?? prev?.pred ?? null);
}

async function resolveDevice(deviceId: string | null): Promise<{ id: string | null; blob: Blob | null }> {
  const id = deviceId || (await redis!.get<string>(ACTIVE_KEY));
  if (!id) return { id: null, blob: null };
  return { id, blob: await redis!.get<Blob>(devKey(id)) };
}

/** Веб → GET /api/live?device=<id>&since=<t>: хураангуй төлөв + шинэ хэмжилтүүд */
export async function cloudLive(deviceId: string | null, since: number) {
  const { id, blob } = await resolveDevice(deviceId);
  if (!id || !blob) return { deviceId: null, snap: buildSnapshot(null, new MemoryRepository()), samples: [] as SensorSample[] };
  const repo = load(blob);
  const snap: Snapshot = buildSnapshot(id, repo);
  if (blob.carry.day === startOfToday()) {
    for (const k of Object.keys(snap.today) as Activity[]) snap.today[k] += blob.carry.totals[k] ?? 0;
  }
  const samples = blob.samples.map(unpack).filter((s) => s.t > since);
  return { deviceId: id, snap, samples };
}

/** Төхөөрөмж сүүлийн үр дүнг татах (compact) */
export async function cloudLatest(deviceId: string | null): Promise<DeviceResponse> {
  const { blob } = await resolveDevice(deviceId);
  return toDeviceResponse(blob?.pred ?? null);
}

/** Түүх: өдрийн жагсаалт + blob дахь сүүлийн хэсгүүд */
export async function cloudHistory(deviceId: string | null) {
  const { id, blob } = await resolveDevice(deviceId);
  if (!id || !blob) return { hours: [], segments: [] };
  const day = startOfToday();
  const now = Date.now();
  const archived = ((await redis!.lrange<Segment | string>(segKey(id, day), 0, -1)) ?? []).map((s) =>
    typeof s === "string" ? (JSON.parse(s) as Segment) : s,
  );
  const segments = [...archived, ...blob.segs].filter((s) => s.end >= day);
  const hours = Array.from({ length: 24 }, (_, h) => {
    const a = day + h * 3600_000;
    if (a > now) return { hour: h, durations: null };
    const b = Math.min(a + 3600_000, now);
    const d = emptyDurations();
    for (const s of segments) d[s.activity] += overlap(s, a, b);
    return { hour: h, durations: d };
  });
  return { deviceId: id, hours, segments, alerts: blob.alerts };
}
