import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Ижил Wi-Fi-д байгаа бусад төхөөрөмж (утас, таблет, өөр компьютер) dev серверийг IP эсвэл
  // <нэр>.local хаягаар нээх боломжтой байхаар (Next.js dev нь өөр origin-ийг анхнаасаа хаадаг)
  allowedDevOrigins: ["10.*.*.*", "192.168.*.*", "172.*.*.*", "*.local"],
};

export default nextConfig;
