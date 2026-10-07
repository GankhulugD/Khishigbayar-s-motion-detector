/**
 * Төслийн нийтлэг өгөгдлийн төрлүүд.
 * Төхөөрөмж (ESP32-S3), сервер (ML), веб гурав энэ гэрээгээр харилцана.
 */

/** Таних хөдөлгөөний ангилал */
export type Activity = "sitting" | "standing" | "walking" | "running" | "lying" | "fall";

/** MPU6050-ийн нэг хэмжилт. Хурдатгал g-ээр, эргэлт °/s-ээр */
export interface SensorSample {
  /** Unix хугацаа (ms) */
  t: number;
  ax: number;
  ay: number;
  az: number;
  gx: number;
  gy: number;
  gz: number;
}

export interface GpsFix {
  lat: number;
  lng: number;
  /** Нарийвчлал (метр) */
  accuracy?: number;
  t: number;
}

/** Төхөөрөмжөөс /api/ingest руу ирэх багц */
export interface IngestPayload {
  deviceId: string;
  samples: SensorSample[];
  gps?: Omit<GpsFix, "t"> & { t?: number };
  battery?: number; // 0–100
  rssi?: number; // dBm
}

/** ML загварын гаргасан үр дүн */
export interface Prediction {
  deviceId: string;
  t: number;
  activity: Activity;
  confidence: number; // 0–1
  /** Бүх ангиллын магадлал */
  scores: Record<Activity, number>;
  model: string;
  latencyMs: number;
}

/** Нэг төрлийн хөдөлгөөн тасралтгүй үргэлжилсэн хэсэг */
export interface Segment {
  activity: Activity;
  start: number;
  end: number;
}

export interface Alert {
  id: string;
  deviceId: string;
  t: number;
  kind: "fall" | "inactivity" | "offline";
  message: string;
  gps?: GpsFix;
  acknowledged: boolean;
}

export interface DeviceStatus {
  deviceId: string;
  name: string;
  online: boolean;
  lastSeen: number;
  battery?: number;
  rssi?: number;
  sampleRateHz: number;
  simulated: boolean;
}

/** Вэб рүү SSE-ээр секунд тутам илгээгдэх хураангуй төлөв */
export interface Snapshot {
  now: number;
  device: DeviceStatus | null;
  current: Prediction | null;
  currentSince: number | null;
  /** Сүүлийн ~10 сек: хурдатгалын хэмжээ ба тэнхлэгүүд */
  signal: { t: number; mag: number; ax: number; ay: number; az: number }[];
  /** Өнөөдрийн ангилал тус бүрийн хугацаа (ms) */
  today: Record<Activity, number>;
  timeline: Segment[];
  alerts: Alert[];
  gps: GpsFix | null;
}

/** Төхөөрөмж /api/ingest-ийн хариуд авах товч үр дүн (OLED-д харуулна) */
export interface DeviceResponse {
  ok: true;
  activity: Activity | null;
  label: string | null;
  confidence: number | null;
  alert: boolean;
}
