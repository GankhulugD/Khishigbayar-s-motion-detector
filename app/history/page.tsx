"use client";

import { useEffect, useState } from "react";
import { HourlyChart } from "@/components/charts";
import { ActivityIcon, Clock, Rings } from "@/components/Icons";
import { Card, CardHeader, PageTitle, Skeleton } from "@/components/ui";
import { ACTIVITIES, ACTIVITY_ORDER, emptyDurations } from "@/lib/activities";
import { fmtClock, fmtDuration } from "@/lib/format";
import type { Activity, Segment } from "@/lib/types";

interface History {
  hours: { hour: number; durations: Record<Activity, number> | null }[];
  segments: Segment[];
}

export default function HistoryPage() {
  const [data, setData] = useState<History | null>(null);
  const [filter, setFilter] = useState<Activity | "all">("all");

  useEffect(() => {
    const load = () => fetch("/api/history", { cache: "no-store" }).then((r) => r.json()).then(setData).catch(() => {});
    load();
    const id = setInterval(load, 10_000);
    return () => clearInterval(id);
  }, []);

  const totals = emptyDurations();
  data?.hours.forEach((h) => h.durations && ACTIVITY_ORDER.forEach((k) => (totals[k] += h.durations![k])));
  const segs = (data?.segments ?? [])
    .filter((s) => s.end - s.start > 5000 && (filter === "all" || s.activity === filter))
    .reverse();

  return (
    <>
      <PageTitle title="Түүх" subtitle="Өнөөдөр" />
      <div className="grid gap-4 sm:grid-cols-3 lg:grid-cols-5">
        {ACTIVITY_ORDER.filter((k) => k !== "fall").map((k) => (
          <button
            key={k}
            onClick={() => setFilter(filter === k ? "all" : k)}
            className={`card p-4 text-left transition ${filter === k ? "ring-2" : "hover:opacity-90"}`}
            style={{ ["--tw-ring-color" as string]: ACTIVITIES[k].color }}
          >
            <span className="flex items-center gap-1.5 text-[13px] font-semibold" style={{ color: ACTIVITIES[k].color }}>
              <ActivityIcon activity={k} size={16} /> {ACTIVITIES[k].noun}
            </span>
            <p className="tabular mt-2 text-[22px] font-semibold">{data ? fmtDuration(totals[k]) : "—"}</p>
          </button>
        ))}
      </div>

      <Card className="mt-4">
        <CardHeader icon={<Rings size={18} />} title="Цаг тутмын хуваарилалт" color="#30b07a" meta="24 цаг" />
        {data ? <HourlyChart hours={data.hours} /> : <Skeleton className="h-60" />}
      </Card>

      <Card className="mt-4">
        <CardHeader
          icon={<Clock size={18} />}
          title="Бүртгэл"
          color="#0a84ff"
          meta={filter === "all" ? `${segs.length} үйлдэл` : ACTIVITIES[filter].short}
        />
        <ul className="divide-y divide-sep">
          {segs.slice(0, 80).map((s, i) => {
            const m = ACTIVITIES[s.activity];
            return (
              <li key={`${s.start}-${i}`} className="flex items-center gap-3 py-3">
                <span className="grid h-9 w-9 place-items-center rounded-[11px]" style={{ background: m.soft, color: m.color }}>
                  <ActivityIcon activity={s.activity} size={20} />
                </span>
                <div>
                  <p className="text-[15px] font-medium">{m.noun}</p>
                  <p className="tabular text-[12px] text-muted">{fmtClock(s.start)} – {fmtClock(s.end)}</p>
                </div>
                <span className="tabular ml-auto text-[14px] text-muted">{fmtDuration(Math.max(60000, s.end - s.start))}</span>
              </li>
            );
          })}
          {data && !segs.length && <li className="py-8 text-center text-[13px] text-muted">Бүртгэл алга</li>}
        </ul>
      </Card>
    </>
  );
}
