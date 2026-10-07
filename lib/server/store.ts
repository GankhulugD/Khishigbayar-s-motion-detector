import { emptyDurations } from "../activities";
import type { Activity, Alert, DeviceStatus, GpsFix, Prediction, SensorSample, Segment } from "../types";

/**
 * Өгөгдлийн агуулахын гэрээ. Demo хувилбар нь санах ойд (in-memory) хадгална.
 * PostgreSQL / TimescaleDB / MongoDB руу шилжихдээ ижил интерфейсийг хэрэгжүүлсэн
 * шинэ класс бичээд getRepository()-г солиход хангалттай.
 */
export interface Repository {
  upsertDevice(d: Partial<DeviceStatus> & { deviceId: string }): DeviceStatus;
  getDevice(deviceId: string): DeviceStatus | undefined;
  listDevices(): DeviceStatus[];
  addSamples(deviceId: string, samples: SensorSample[]): void;
  getWindow(deviceId: string, ms: number): SensorSample[];
  addPrediction(p: Prediction): void;
  latestPrediction(deviceId: string): Prediction | null;
  segments(deviceId: string, since: number): Segment[];
  setGps(deviceId: string, fix: GpsFix): void;
  getGps(deviceId: string): GpsFix | null;
  addAlert(a: Omit<Alert, "id" | "acknowledged">): Alert;
  alerts(deviceId: string, limit?: number): Alert[];
  durations(deviceId: string, since: number, until: number): Record<Activity, number>;
}

const MAX_SAMPLES = 3000; // ~60 сек @ 50 Hz
const MAX_SEGMENTS = 5000;

interface DeviceState {
  samples: SensorSample[];
  predictions: Prediction[];
  segments: Segment[];
  gps: GpsFix | null;
  alerts: Alert[];
}

class MemoryRepository implements Repository {
  private devices = new Map<string, DeviceStatus>();
  private state = new Map<string, DeviceState>();
  private alertSeq = 0;

  private s(id: string): DeviceState {
    let st = this.state.get(id);
    if (!st) {
      st = { samples: [], predictions: [], segments: [], gps: null, alerts: [] };
      this.state.set(id, st);
    }
    return st;
  }

  upsertDevice(d: Partial<DeviceStatus> & { deviceId: string }): DeviceStatus {
    const prev = this.devices.get(d.deviceId);
    const next: DeviceStatus = {
      name: d.deviceId,
      online: true,
      lastSeen: Date.now(),
      sampleRateHz: 50,
      simulated: false,
      ...prev,
      ...Object.fromEntries(Object.entries(d).filter(([, v]) => v !== undefined)),
    } as DeviceStatus;
    this.devices.set(d.deviceId, next);
    return next;
  }

  getDevice(id: string) {
    return this.devices.get(id);
  }

  listDevices() {
    return [...this.devices.values()];
  }

  addSamples(id: string, samples: SensorSample[]) {
    const st = this.s(id);
    st.samples.push(...samples);
    if (st.samples.length > MAX_SAMPLES) st.samples.splice(0, st.samples.length - MAX_SAMPLES);
  }

  getWindow(id: string, ms: number) {
    const st = this.s(id);
    if (!st.samples.length) return [];
    const end = st.samples[st.samples.length - 1].t;
    return st.samples.filter((x) => x.t > end - ms);
  }

  addPrediction(p: Prediction) {
    const st = this.s(p.deviceId);
    st.predictions.push(p);
    if (st.predictions.length > 600) st.predictions.shift();
    const last = st.segments[st.segments.length - 1];
    if (last && last.activity === p.activity && p.t - last.end < 5000) last.end = p.t;
    else st.segments.push({ activity: p.activity, start: last && p.t - last.end < 5000 ? last.end : p.t - 1000, end: p.t });
    if (st.segments.length > MAX_SEGMENTS) st.segments.shift();
  }

  /** Simulator-ийн түүхэн өгөгдөл нөхөх зориулалттай */
  pushSegment(id: string, seg: Segment) {
    this.s(id).segments.push(seg);
  }

  latestPrediction(id: string) {
    const p = this.s(id).predictions;
    return p.length ? p[p.length - 1] : null;
  }

  segments(id: string, since: number) {
    return this.s(id).segments.filter((x) => x.end >= since);
  }

  setGps(id: string, fix: GpsFix) {
    this.s(id).gps = fix;
  }

  getGps(id: string) {
    return this.s(id).gps;
  }

  addAlert(a: Omit<Alert, "id" | "acknowledged">): Alert {
    const alert: Alert = { ...a, id: `al_${++this.alertSeq}`, acknowledged: false };
    const list = this.s(a.deviceId).alerts;
    list.unshift(alert);
    if (list.length > 100) list.pop();
    return alert;
  }

  alerts(id: string, limit = 20) {
    return this.s(id).alerts.slice(0, limit);
  }

  durations(id: string, since: number, until: number) {
    const out = emptyDurations();
    for (const seg of this.s(id).segments) {
      const a = Math.max(seg.start, since);
      const b = Math.min(seg.end, until);
      if (b > a) out[seg.activity] += b - a;
    }
    return out;
  }
}

// Next.js dev горимд модуль дахин ачаалагдахад төлөв алдагдахгүйн тулд globalThis-д хадгална
const g = globalThis as unknown as { __repo?: MemoryRepository };
export function getRepository(): MemoryRepository {
  if (!g.__repo) g.__repo = new MemoryRepository();
  return g.__repo;
}
