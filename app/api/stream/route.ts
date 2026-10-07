import { bus, buildSnapshot } from "@/lib/server/pipeline";
import { ensureSimulator } from "@/lib/server/simulator";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

/** Server-Sent Events: веб самбар руу бодит хугацааны төлөвийг түлхэнэ */
export async function GET(req: Request) {
  ensureSimulator();
  const enc = new TextEncoder();
  let cleanup = () => {};

  const stream = new ReadableStream({
    start(controller) {
      let pending = false;
      const send = () => {
        pending = false;
        try {
          controller.enqueue(enc.encode(`data: ${JSON.stringify(buildSnapshot())}\n\n`));
        } catch {
          cleanup();
        }
      };
      // Олон update ирэхэд 250 ms-д нэг удаа нэгтгэж илгээнэ
      const onUpdate = () => {
        if (!pending) {
          pending = true;
          setTimeout(send, 250);
        }
      };
      const heartbeat = setInterval(send, 2000);
      bus.on("update", onUpdate);
      send();
      cleanup = () => {
        clearInterval(heartbeat);
        bus.off("update", onUpdate);
      };
      req.signal.addEventListener("abort", () => {
        cleanup();
        try { controller.close(); } catch {}
      });
    },
    cancel() {
      cleanup();
    },
  });

  return new Response(stream, {
    headers: {
      "content-type": "text/event-stream; charset=utf-8",
      "cache-control": "no-cache, no-transform",
      connection: "keep-alive",
    },
  });
}
