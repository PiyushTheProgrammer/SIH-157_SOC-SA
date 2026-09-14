import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Air-gapped deployment: no external image domains
  images: { unoptimized: true },
  // Suppress noisy hydration warnings from browser extensions
  reactStrictMode: true,
  async rewrites() {
    return [
      { source: "/assessment", destination: "/" },
      { source: "/findings", destination: "/" },
      { source: "/evidence", destination: "/" },
      { source: "/assets", destination: "/" },
      { source: "/data", destination: "/" },
      { source: "/reports", destination: "/" },
      { source: "/prioritizer", destination: "/" },
    ];
  },
};

export default nextConfig;
