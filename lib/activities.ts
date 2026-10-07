import type { Activity } from "./types";

export interface ActivityMeta {
  key: Activity;
  label: string;
  /** Нэр үг хэлбэр (түүх, жагсаалтад) */
  noun: string;
  /** OLED дэлгэц дээр харуулах латин нэр */
  short: string;
  color: string;
  soft: string;
  description: string;
}

export const ACTIVITIES: Record<Activity, ActivityMeta> = {
  sitting: { key: "sitting", noun: "Суух", label: "Сууж байна", short: "Sitting", color: "#5E5CE6", soft: "#EEEEFD", description: "Тогтвортой байрлал, бага хурдатгал" },
  standing: { key: "standing", noun: "Зогсох", label: "Зогсож байна", short: "Standing", color: "#0A84FF", soft: "#E6F2FF", description: "Босоо байрлал, бага хэлбэлзэл" },
  walking: { key: "walking", noun: "Алхах", label: "Алхаж байна", short: "Walking", color: "#30B07A", soft: "#E5F6EE", description: "Тогтмол давтамжтай хэлбэлзэл" },
  running: { key: "running", noun: "Гүйх", label: "Гүйж байна", short: "Running", color: "#FF9F0A", soft: "#FFF3E0", description: "Өндөр далайц, өндөр давтамж" },
  lying: { key: "lying", noun: "Хэвтэх", label: "Хэвтэж байна", short: "Lying", color: "#8E8E93", soft: "#F1F1F3", description: "Таталцлын тэнхлэг хэвтээ" },
  fall: { key: "fall", noun: "Уналт", label: "Уналт илэрлээ", short: "FALL!", color: "#FF3B30", soft: "#FFE9E7", description: "Огцом цохилт → хөдөлгөөнгүй" },
};

export const ACTIVITY_ORDER: Activity[] = ["sitting", "standing", "walking", "running", "lying", "fall"];

export const emptyDurations = (): Record<Activity, number> => ({
  sitting: 0, standing: 0, walking: 0, running: 0, lying: 0, fall: 0,
});
