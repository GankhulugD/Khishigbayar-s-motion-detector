"use client";

import { Brain, Chip, Pulse } from "@/components/Icons";
import { useLive } from "@/components/LiveProvider";
import { DeviceCard } from "@/components/dashboard";
import { Card, CardHeader, PageTitle } from "@/components/ui";
import { ACTIVITIES } from "@/lib/activities";

const FLOW = [
  { n: 1, t: "MPU6050 + GPS", d: "ESP32-S3 ~50 Hz давтамжтай хэмжинэ" },
  { n: 2, t: "Wi-Fi → /api/ingest", d: "0.5 сек тутам багцалж илгээнэ" },
  { n: 3, t: "Сервер ML", d: "2 сек цонхоор ангилна" },
  { n: 4, t: "Үр дүн", d: "Төхөөрөмж (OLED, buzzer) ба веб" },
];

const SAMPLE = `curl -X POST http://localhost:3000/api/ingest \\
  -H "content-type: application/json" \\
  -H "x-device-key: dev-secret-key" \\
  -d '{
    "deviceId": "esp32-01",
    "battery": 92, "rssi": -60,
    "gps": { "lat": 47.9184, "lng": 106.9177, "accuracy": 2.5 },
    "samples": [
      { "t": 1730000000000, "ax": 0.05, "ay": 0.99, "az": 0.08, "gx": 0.4, "gy": -0.2, "gz": 0.1 }
    ]
  }'`;

const RESPONSE = `{ "ok": true, "activity": "walking", "label": "Walking", "confidence": 0.94, "alert": false }`;

export default function DevicePage() {
  const { snap } = useLive();
  const p = snap?.current;

  return (
    <>
      <PageTitle title="Төхөөрөмж" subtitle="ESP32-S3 · MPU6050 · GPS" />
      <div className="grid gap-4 lg:grid-cols-3">
        <div className="space-y-4">
          {snap && <DeviceCard snap={snap} />}
          <Card>
            <CardHeader icon={<Chip size={18} />} title="OLED дэлгэц" color="#1c1c1e" meta="серверийн хариу" />
            <div className="rounded-2xl bg-[#1c1c1e] p-2">
              <div className="grid h-36 place-items-center rounded-xl bg-black font-mono text-center">
                {p?.activity === "fall" ? (
                  <div className="text-[#ff6b61]">
                    <p className="text-lg font-bold">WARNING!</p>
                    <p className="text-xs">FALL DETECTED</p>
                  </div>
                ) : (
                  <div className="text-white">
                    <p className="text-[10px] tracking-widest text-[#8fd3ff]">MOTION STATUS</p>
                    <p className="text-2xl font-bold">{p ? ACTIVITIES[p.activity].short : "---"}</p>
                    <p className="text-xs">Confidence: {p ? Math.round(p.confidence * 100) : 0}%</p>
                  </div>
                )}
              </div>
            </div>
          </Card>
        </div>

        <div className="space-y-4 lg:col-span-2">
          <Card>
            <CardHeader icon={<Pulse size={18} />} title="Өгөгдлийн урсгал" color="#ff375f" />
            <ol className="grid gap-3 sm:grid-cols-4">
              {FLOW.map((f) => (
                <li key={f.n} className="rounded-2xl bg-fill p-4">
                  <span className="grid h-7 w-7 place-items-center rounded-full bg-[#ff375f] text-[13px] font-bold text-white">{f.n}</span>
                  <p className="mt-3 text-[14px] font-semibold">{f.t}</p>
                  <p className="mt-1 text-[12px] text-muted">{f.d}</p>
                </li>
              ))}
            </ol>
          </Card>

          <Card>
            <CardHeader icon={<Chip size={18} />} title="Төхөөрөмжийн API" color="#0a84ff" meta="REST · JSON" />
            <div className="space-y-2 text-[14px]">
              {[
                ["POST", "/api/ingest", "Мэдрэгч + GPS өгөгдөл илгээх, хариуд ангиллын үр дүн авна"],
                ["GET", "/api/snapshot?device=<id>&compact=1", "Сүүлийн үр дүнг татах (OLED)"],
                ["GET", "/api/stream", "Веб самбарын SSE урсгал"],
                ["GET", "/api/history", "Өнөөдрийн түүх"],
              ].map(([m, path, d]) => (
                <div key={path} className="flex flex-wrap items-center gap-2 rounded-xl bg-fill px-3 py-2">
                  <span className={`rounded-md px-1.5 py-0.5 text-[11px] font-bold text-white ${m === "POST" ? "bg-[#30b07a]" : "bg-[#0a84ff]"}`}>{m}</span>
                  <code className="text-[13px]">{path}</code>
                  <span className="ml-auto text-[12px] text-muted">{d}</span>
                </div>
              ))}
            </div>
            <p className="mt-4 text-[13px] font-semibold">Жишээ хүсэлт</p>
            <pre className="mt-2 overflow-x-auto rounded-2xl bg-[#1c1c1e] p-4 text-[12px] leading-relaxed text-[#e5e5ea]">{SAMPLE}</pre>
            <p className="mt-4 text-[13px] font-semibold">Хариу (төхөөрөмж OLED / buzzer-т ашиглана)</p>
            <pre className="mt-2 overflow-x-auto rounded-2xl bg-[#1c1c1e] p-4 text-[12px] text-[#e5e5ea]">{RESPONSE}</pre>
          </Card>

          <Card>
            <CardHeader icon={<Brain size={18} />} title="ML загвар" color="#5e5ce6" meta={p?.model} />
            <p className="text-[14px] leading-relaxed text-muted">
              Одоогоор серверт baseline ангилагч ажиллаж байна. Сургасан загвараа <code className="text-ink">ml/</code> хавтас дахь Python
              үйлчилгээгээр ажиллуулаад <code className="text-ink">ML_SERVICE_URL</code>-г тохируулахад вэб систем автоматаар шилжинэ.
            </p>
          </Card>
        </div>
      </div>
    </>
  );
}
