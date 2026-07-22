import type { NextConfig } from "next";

// Dev origins for Next.js cross-origin checks. Prefer localhost; add LAN
// host via NEXT_PUBLIC_DEV_HOST if needed (never commit machine-specific IPs).
const devHost = process.env.NEXT_PUBLIC_DEV_HOST?.trim();
const allowedDevOrigins = [
  "http://localhost:3001",
  "http://127.0.0.1:3001",
  ...(devHost
    ? [`http://${devHost.replace(/^https?:\/\//, "").replace(/\/$/, "")}:3001`]
    : []),
];

const nextConfig: NextConfig = {
  reactStrictMode: true,
  allowedDevOrigins,
};

export default nextConfig;
