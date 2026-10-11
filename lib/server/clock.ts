import type { SensorSample } from "../types";

export interface DeviceClock {
  offset: number;
  lastT: number;
}

/**
 * Төхөөрөмж millis() илгээдэг тул серверийн цагт шилжүүлнэ.
 * Төхөөрөмж бүрийн зөрүүг хадгалж, багц хоорондын цагийн үсрэлтээс сэргийлнэ.
 */
export function alignClock(samples: SensorSample[], prev: DeviceClock | undefined, now = Date.now()) {
  const last = samples[samples.length - 1].t;
  let offset: number;
  if (Math.abs(now - last) <= 60_000) offset = 0; // төхөөрөмж бодит цаг илгээсэн
  else if (!prev || last < prev.lastT || now - (last + prev.offset) < -1_000 || now - (last + prev.offset) > 30_000)
    offset = now - last; // анхны холболт, reboot эсвэл их зөрүү
  else offset = prev.offset;
  return { samples: samples.map((s) => ({ ...s, t: s.t + offset })), clock: { offset, lastT: last } };
}
