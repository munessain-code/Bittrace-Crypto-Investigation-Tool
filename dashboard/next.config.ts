import type { NextConfig } from "next";

const serverIP = "192.168.101.144";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  allowedDevOrigins: [`http://${serverIP}:3001`],
};

export default nextConfig;
