"use client";

import { createContext, useContext, useEffect, useRef, useState } from "react";
import type { Snapshot } from "@/lib/types";

type Conn = "connecting" | "live" | "reconnecting";

const Ctx = createContext<{ snap: Snapshot | null; conn: Conn }>({ snap: null, conn: "connecting" });

/**
 * Серверээс бодит хугацааны төлөвийг SSE (/api/stream)-ээр хүлээн авна.
 * SSE тасарвал /api/snapshot-ийг 2 сек тутам асууж (polling) үргэлжлүүлнэ.
 */
export function LiveProvider({ children }: { children: React.ReactNode }) {
  const [snap, setSnap] = useState<Snapshot | null>(null);
  const [conn, setConn] = useState<Conn>("connecting");
  const poll = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    let es: EventSource | null = null;
    let closed = false;

    const startPolling = () => {
      if (poll.current) return;
      poll.current = setInterval(async () => {
        try {
          const r = await fetch("/api/snapshot", { cache: "no-store" });
          if (r.ok) setSnap(await r.json());
        } catch {}
      }, 2000);
    };
    const stopPolling = () => {
      if (poll.current) clearInterval(poll.current);
      poll.current = null;
    };

    const connect = () => {
      es = new EventSource("/api/stream");
      es.onopen = () => {
        setConn("live");
        stopPolling();
      };
      es.onmessage = (e) => {
        setSnap(JSON.parse(e.data));
        setConn("live");
      };
      es.onerror = () => {
        setConn("reconnecting");
        startPolling();
        es?.close();
        if (!closed) setTimeout(connect, 3000);
      };
    };
    connect();
    return () => {
      closed = true;
      es?.close();
      stopPolling();
    };
  }, []);

  return <Ctx.Provider value={{ snap, conn }}>{children}</Ctx.Provider>;
}

export const useLive = () => useContext(Ctx);
