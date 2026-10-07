export function fmtDuration(ms: number): string {
  const totalMin = Math.round(ms / 60000);
  const h = Math.floor(totalMin / 60);
  const m = totalMin % 60;
  if (h === 0) return `${m} мин`;
  return m === 0 ? `${h} цаг` : `${h} цаг ${m} мин`;
}

export function fmtClock(t: number): string {
  const d = new Date(t);
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

export function fmtElapsed(ms: number): string {
  const s = Math.max(0, Math.floor(ms / 1000));
  const m = Math.floor(s / 60);
  const h = Math.floor(m / 60);
  if (h > 0) return `${h} цаг ${m % 60} мин`;
  if (m > 0) return `${m} мин ${s % 60} сек`;
  return `${s} сек`;
}

export function fmtAgo(ms: number): string {
  const s = Math.floor(ms / 1000);
  if (s < 5) return "сая";
  if (s < 60) return `${s} сек өмнө`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m} мин өмнө`;
  return `${Math.floor(m / 60)} цаг өмнө`;
}
