import type { Activity } from "@/lib/types";

type P = { className?: string; size?: number };

function Svg({ size = 20, className, children, fill = false }: P & { children: React.ReactNode; fill?: boolean }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill={fill ? "currentColor" : "none"}
      stroke={fill ? "none" : "currentColor"}
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden
    >
      {children}
    </svg>
  );
}

const Head = ({ cx, cy }: { cx: number; cy: number }) => <circle cx={cx} cy={cy} r={2} fill="currentColor" stroke="none" />;

export function ActivityIcon({ activity, ...p }: P & { activity: Activity }) {
  switch (activity) {
    case "sitting":
      return (
        <Svg {...p}>
          <Head cx={9} cy={4} />
          <path d="M9 7v6h6l1 7" />
          <path d="M9 10l4 1" />
          <path d="M6 9v9h4" />
        </Svg>
      );
    case "standing":
      return (
        <Svg {...p}>
          <Head cx={12} cy={4} />
          <path d="M12 7v7M12 14l-2 7M12 14l2 7M8 10l4-2 4 2" />
        </Svg>
      );
    case "walking":
      return (
        <Svg {...p}>
          <Head cx={13} cy={4} />
          <path d="M12 8l-1 6 3 3 1 4M11 14l-2 3-3 1M12 8l3 3 3 1M12 8l-3 2-1 3" />
        </Svg>
      );
    case "running":
      return (
        <Svg {...p}>
          <Head cx={15} cy={4} />
          <path d="M13 8l-3 5 4 2-1 6M10 13l-3 1-2 3M13 8l3 3 4 0M13 8l-4 1-2 3" />
        </Svg>
      );
    case "lying":
      return (
        <Svg {...p}>
          <path d="M3 18V8M3 14h18v4M21 14v-2a3 3 0 0 0-3-3h-7v5" />
          <circle cx={7} cy={11} r={1.8} fill="currentColor" stroke="none" />
        </Svg>
      );
    case "fall":
      return (
        <Svg {...p}>
          <path d="M12 3l9.5 17h-19z" />
          <path d="M12 10v4M12 17.5v.01" />
        </Svg>
      );
  }
}

export const Pulse = (p: P) => (
  <Svg {...p}>
    <path d="M3 12h4l2-5 4 10 2-5h6" />
  </Svg>
);
export const Pin = (p: P) => (
  <Svg {...p}>
    <path d="M12 21s-7-6.2-7-11.5a7 7 0 0 1 14 0C19 14.8 12 21 12 21z" />
    <circle cx={12} cy={9.5} r={2.5} />
  </Svg>
);
export const Bell = (p: P) => (
  <Svg {...p}>
    <path d="M6 16V11a6 6 0 0 1 12 0v5l2 2H4z" />
    <path d="M10 20a2 2 0 0 0 4 0" />
  </Svg>
);
export const Chip = (p: P) => (
  <Svg {...p}>
    <rect x={6} y={6} width={12} height={12} rx={2} />
    <path d="M9 2v4M15 2v4M9 18v4M15 18v4M2 9h4M2 15h4M18 9h4M18 15h4" />
  </Svg>
);
export const Wave = (p: P) => (
  <Svg {...p}>
    <path d="M2 12c2-6 4-6 6 0s4 6 6 0 4-6 6 0" />
  </Svg>
);
export const Clock = (p: P) => (
  <Svg {...p}>
    <circle cx={12} cy={12} r={9} />
    <path d="M12 7v5l3 2" />
  </Svg>
);
export const Rings = (p: P) => (
  <Svg {...p}>
    <circle cx={12} cy={12} r={9} />
    <circle cx={12} cy={12} r={5} />
  </Svg>
);
export const Chevron = (p: P) => (
  <Svg {...p}>
    <path d="M9 6l6 6-6 6" />
  </Svg>
);
export const Brain = (p: P) => (
  <Svg {...p}>
    <path d="M9 4a3 3 0 0 0-3 3 3 3 0 0 0-2 5 3 3 0 0 0 2 5 3 3 0 0 0 6 1V5a2 2 0 0 0-3-1z" />
    <path d="M15 4a3 3 0 0 1 3 3 3 3 0 0 1 2 5 3 3 0 0 1-2 5 3 3 0 0 1-6 1" />
  </Svg>
);
export const Battery = ({ level = 100, ...p }: P & { level?: number }) => (
  <Svg {...p}>
    <rect x={2} y={7} width={18} height={10} rx={2.5} />
    <path d="M22 11v2" />
    <rect x={4} y={9} width={Math.max(1, (14 * level) / 100)} height={6} rx={1} fill="currentColor" stroke="none" />
  </Svg>
);
export const Signal = (p: P) => (
  <Svg {...p}>
    <path d="M5 18v-2M10 18v-5M15 18v-8M20 18V6" />
  </Svg>
);
