"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useLive } from "./LiveProvider";

const TABS = [
  { href: "/", label: "Хураангуй" },
  { href: "/history", label: "Түүх" },
  { href: "/device", label: "Төхөөрөмж" },
];

export function Nav() {
  const path = usePathname();
  const { snap, conn } = useLive();
  const online = conn === "live" && snap?.device?.online;

  return (
    <header className="sticky top-0 z-30 border-b border-sep bg-bg/80 backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-6xl items-center gap-4 px-4 sm:px-6">
        <Link href="/" className="flex items-center gap-2.5">
          <span className="grid h-8 w-8 place-items-center rounded-[9px] bg-gradient-to-br from-[#ff5e7a] to-[#ff2d55] text-white shadow-sm">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
              <path d="M3 12h4l2-5 4 10 2-5h6" />
            </svg>
          </span>
          <span className="hidden text-[17px] font-semibold tracking-tight sm:inline">MotionCare</span>
        </Link>

        <nav className="ml-auto flex rounded-[10px] bg-fill p-0.5 text-[13px] font-medium sm:ml-6">
          {TABS.map((t) => {
            const active = t.href === "/" ? path === "/" : path.startsWith(t.href);
            return (
              <Link
                key={t.href}
                href={t.href}
                className={`whitespace-nowrap rounded-[8px] px-2.5 py-1.5 transition sm:px-3 ${active ? "bg-card text-ink shadow-sm" : "text-muted hover:text-ink"}`}
              >
                {t.label}
              </Link>
            );
          })}
        </nav>

        <div className="ml-auto hidden items-center gap-2 text-[13px] text-muted sm:flex">
          <span className={`h-2 w-2 rounded-full ${online ? "live-dot bg-[#30b07a]" : "bg-[#c7c7cc]"}`} />
          {online ? "Шууд" : conn === "reconnecting" ? "Дахин холбогдож байна" : snap?.device ? "Офлайн" : "Холбогдож байна"}
          {snap?.device?.simulated && (
            <span className="rounded-full bg-[#fff3e0] px-2 py-0.5 text-[11px] font-semibold text-[#c77700]">DEMO</span>
          )}
        </div>
      </div>
    </header>
  );
}
