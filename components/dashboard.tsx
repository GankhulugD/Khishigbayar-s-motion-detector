"use client";

import { ACTIVITIES, ACTIVITY_ORDER } from "@/lib/activities";
import { fmtAgo, fmtClock, fmtDuration, fmtElapsed } from "@/lib/format";
import type { Snapshot } from "@/lib/types";
import { ActivityRings, DayBar, SignalChart } from "./charts";
import { ActivityIcon, Battery, Bell, Brain, Chip, Clock, Pin, Rings, Signal, Wave } from "./Icons";
import { BigValue, Card, CardHeader, Skeleton } from "./ui";

/** Одоогийн хөдөлгөөн — гол карт */
export function CurrentActivityCard({ snap }: { snap: Snapshot }) {
  const p = snap.current;
  if (!p) return <Card className="min-h-[220px]"><Skeleton className="h-full min-h-[180px]" /></Card>;
  const meta = ACTIVITIES[p.activity];
  const isFall = p.activity === "fall";
  return (
    <section
      className="card relative overflow-hidden p-6"
      style={{ background: isFall ? meta.color : undefined }}
    >
      <div
        className="pointer-events-none absolute -right-16 -top-16 h-64 w-64 rounded-full opacity-60 blur-3xl dark:opacity-15"
        style={{ background: isFall ? "#ffffff33" : meta.soft }}
      />
      <div className={`relative flex items-center gap-1.5 text-[15px] font-semibold ${isFall ? "text-white" : ""}`} style={{ color: isFall ? undefined : meta.color }}>
        <Wave size={18} /> Одоогийн төлөв
        <span className={`ml-auto text-[13px] font-normal ${isFall ? "text-white/80" : "text-muted"}`}>{fmtClock(p.t)}</span>
      </div>
      <div key={p.activity} className="fade-up relative mt-6 flex items-center gap-5">
        <span
          className="grid h-20 w-20 shrink-0 place-items-center rounded-[22px]"
          style={{ background: isFall ? "#ffffff" : meta.color, color: isFall ? meta.color : "#fff" }}
        >
          <ActivityIcon activity={p.activity} size={44} />
        </span>
        <div className={isFall ? "text-white" : ""}>
          <h2 className="text-[32px] font-bold leading-tight tracking-tight">{meta.label}</h2>
          <p className={`mt-1 text-[15px] ${isFall ? "text-white/85" : "text-muted"}`}>
            {snap.currentSince ? `${fmtElapsed(snap.now - snap.currentSince)} үргэлжилж байна` : meta.description}
          </p>
        </div>
      </div>
      <div className={`relative mt-6 flex items-end justify-between ${isFall ? "text-white" : ""}`}>
        <div>
          <p className={`text-[13px] ${isFall ? "text-white/80" : "text-muted"}`}>Итгэлцэл</p>
          <BigValue value={Math.round(p.confidence * 100)} unit="%" />
        </div>
        <div className="w-1/2">
          <div className={`h-2 overflow-hidden rounded-full ${isFall ? "bg-white/30" : "bg-fill"}`}>
            <div className="h-full rounded-full transition-all duration-500" style={{ width: `${p.confidence * 100}%`, background: isFall ? "#fff" : meta.color }} />
          </div>
          <p className={`mt-2 text-right text-[12px] ${isFall ? "text-white/80" : "text-muted"}`}>
            {p.model} · {p.latencyMs.toFixed(1)} ms
          </p>
        </div>
      </div>
    </section>
  );
}

/** Бүх ангиллын магадлал */
export function ScoresCard({ snap }: { snap: Snapshot }) {
  const s = snap.current?.scores;
  return (
    <Card>
      <CardHeader icon={<Brain size={18} />} title="ML ангилал" color="#5e5ce6" meta="2 сек цонх" />
      <div className="space-y-3">
        {ACTIVITY_ORDER.map((k) => {
          const v = s?.[k] ?? 0;
          return (
            <div key={k} className="flex items-center gap-3">
              <span className="grid h-7 w-7 shrink-0 place-items-center rounded-lg" style={{ background: ACTIVITIES[k].soft, color: ACTIVITIES[k].color }}>
                <ActivityIcon activity={k} size={16} />
              </span>
              <span className="w-16 text-[13px]">{ACTIVITIES[k].noun}</span>
              <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-fill">
                <div className="h-full rounded-full transition-all duration-500" style={{ width: `${v * 100}%`, background: ACTIVITIES[k].color }} />
              </div>
              <span className="tabular w-10 text-right text-[13px] font-semibold">{Math.round(v * 100)}%</span>
            </div>
          );
        })}
      </div>
    </Card>
  );
}

export function SignalCard({ snap }: { snap: Snapshot }) {
  const last = snap.signal[snap.signal.length - 1];
  return (
    <Card>
      <CardHeader icon={<Wave size={18} />} title="Мэдрэгчийн дохио" color="#ff375f" meta="MPU6050" />
      <div className="flex flex-wrap items-end gap-x-8 gap-y-2">
        <div>
          <p className="text-[13px] text-muted">Хурдатгалын хэмжээ</p>
          <BigValue value={last ? last.mag.toFixed(2) : "—"} unit="g" />
        </div>
        <div className="flex gap-4 pb-1 text-[12px] text-muted">
          <span className="flex items-center gap-1.5"><i className="h-2 w-2 rounded-full bg-[#ff375f]" />|a|</span>
          <span className="flex items-center gap-1.5"><i className="h-2 w-2 rounded-full bg-[#0a84ff]" />aY</span>
          <span className="flex items-center gap-1.5"><i className="h-2 w-2 rounded-full bg-[#5e5ce6]" />aZ</span>
        </div>
      </div>
      <div className="mt-3">{snap.signal.length ? <SignalChart data={snap.signal} now={snap.now} /> : <Skeleton className="h-44" />}</div>
    </Card>
  );
}

export function TodayCard({ snap }: { snap: Snapshot }) {
  const t = snap.today;
  const active = t.walking + t.running;
  const standing = t.standing + active;
  const rings = [
    { label: "Идэвхтэй", value: active / 60000, goal: 30, color: "#30b07a", unit: "мин" },
    { label: "Босоо", value: standing / 60000, goal: 120, color: "#0a84ff", unit: "мин" },
  ];
  return (
    <Card>
      <CardHeader icon={<Rings size={18} />} title="Өнөөдрийн идэвх" color="#30b07a" meta="00:00-ээс" href="/history" />
      <div className="flex items-center gap-6">
        <ActivityRings rings={rings} />
        <div className="space-y-4">
          {rings.map((r) => (
            <div key={r.label}>
              <p className="text-[13px] font-semibold" style={{ color: r.color }}>{r.label}</p>
              <p className="tabular text-[22px] font-semibold leading-tight">
                {Math.round(r.value)}<span className="text-[15px] text-muted">/{r.goal} {r.unit}</span>
              </p>
            </div>
          ))}
        </div>
      </div>
      <div className="mt-6">
        <DayBar today={t} />
      </div>
    </Card>
  );
}

export function TimelineCard({ snap }: { snap: Snapshot }) {
  const items = [...snap.timeline].reverse().filter((s) => s.end - s.start > 3000).slice(0, 7);
  return (
    <Card>
      <CardHeader icon={<Clock size={18} />} title="Хөдөлгөөний түүх" color="#0a84ff" href="/history" meta="Бүгд" />
      <ul className="divide-y divide-sep">
        {items.map((s, i) => {
          const m = ACTIVITIES[s.activity];
          return (
            <li key={`${s.start}-${i}`} className="flex items-center gap-3 py-2.5">
              <span className="grid h-8 w-8 place-items-center rounded-[10px]" style={{ background: m.soft, color: m.color }}>
                <ActivityIcon activity={s.activity} size={18} />
              </span>
              <div className="min-w-0">
                <p className="text-[15px] font-medium">{m.noun}</p>
                <p className="tabular text-[12px] text-muted">{fmtClock(s.start)} – {fmtClock(s.end)}</p>
              </div>
              <span className="tabular ml-auto text-[13px] text-muted">{fmtDuration(Math.max(60000, s.end - s.start))}</span>
            </li>
          );
        })}
        {!items.length && <li className="py-6 text-center text-[13px] text-muted">Одоогоор бүртгэл алга</li>}
      </ul>
    </Card>
  );
}

export function LocationCard({ snap }: { snap: Snapshot }) {
  const g = snap.gps;
  const d = 0.004;
  return (
    <Card className="overflow-hidden !p-0">
      <div className="p-5 pb-3">
        <CardHeader icon={<Pin size={18} />} title="Байршил" color="#ff9f0a" meta={g ? fmtAgo(snap.now - g.t) : undefined} />
        {g ? (
          <p className="tabular text-[15px] font-medium">
            {g.lat.toFixed(5)}° N, {g.lng.toFixed(5)}° E
            {g.accuracy && <span className="ml-2 text-[13px] font-normal text-muted">±{g.accuracy} м</span>}
          </p>
        ) : (
          <p className="text-[13px] text-muted">GPS өгөгдөл хүлээж байна…</p>
        )}
      </div>
      {g && (
        <iframe
          title="Байршлын зураг"
          className="h-56 w-full border-0"
          loading="lazy"
          src={`https://www.openstreetmap.org/export/embed.html?bbox=${g.lng - d},${g.lat - d / 2},${g.lng + d},${g.lat + d / 2}&layer=mapnik&marker=${g.lat},${g.lng}`}
        />
      )}
    </Card>
  );
}

export function AlertsCard({ snap }: { snap: Snapshot }) {
  return (
    <Card>
      <CardHeader icon={<Bell size={18} />} title="Анхааруулга" color="#ff3b30" meta={`${snap.alerts.length}`} />
      {snap.alerts.length ? (
        <ul className="space-y-2">
          {snap.alerts.slice(0, 4).map((a) => (
            <li key={a.id} className="flex items-start gap-3 rounded-2xl bg-[#ff3b30]/8 p-3">
              <span className="mt-0.5 text-[#ff3b30]"><ActivityIcon activity="fall" size={18} /></span>
              <div className="min-w-0">
                <p className="text-[14px] font-semibold">{a.message}</p>
                <p className="tabular text-[12px] text-muted">
                  {fmtClock(a.t)} · {fmtAgo(snap.now - a.t)}
                  {a.gps && ` · ${a.gps.lat.toFixed(4)}, ${a.gps.lng.toFixed(4)}`}
                </p>
              </div>
            </li>
          ))}
        </ul>
      ) : (
        <div className="flex items-center gap-3 rounded-2xl bg-[#30b07a]/10 p-3 text-[14px]">
          <span className="text-[#30b07a]">●</span> Хэвийн — анхааруулга алга
        </div>
      )}
    </Card>
  );
}

export function DeviceCard({ snap }: { snap: Snapshot }) {
  const d = snap.device;
  const rows = d
    ? [
        { icon: <Signal size={16} />, label: "Холболт", value: d.online ? `Онлайн · ${d.rssi ?? "–"} dBm` : `Офлайн · ${fmtAgo(snap.now - d.lastSeen)}` },
        { icon: <Battery size={16} level={d.battery ?? 0} />, label: "Батерей", value: d.battery != null ? `${d.battery}%` : "–" },
        { icon: <Wave size={16} />, label: "Давтамж", value: `${d.sampleRateHz} Hz` },
        { icon: <Clock size={16} />, label: "Сүүлд", value: fmtAgo(snap.now - d.lastSeen) },
      ]
    : [];
  return (
    <Card>
      <CardHeader icon={<Chip size={18} />} title="Төхөөрөмж" color="#8e8e93" href="/device" meta={d?.name} />
      <ul className="divide-y divide-sep">
        {rows.map((r) => (
          <li key={r.label} className="flex items-center gap-3 py-2 text-[14px]">
            <span className="text-muted">{r.icon}</span>
            <span className="text-muted">{r.label}</span>
            <span className="tabular ml-auto font-medium">{r.value}</span>
          </li>
        ))}
      </ul>
    </Card>
  );
}
