import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Air-gapped deployment: no external image domains
  images: { unoptimized: true },
  // Suppress noisy hydration warnings from browser extensions
  reactStrictMode: true,
};

export default nextConfig;
