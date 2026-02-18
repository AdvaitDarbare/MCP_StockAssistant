import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/py/:path*",
        destination: "http://127.0.0.1:8001/api/:path*", // Proxy to FastAPI
      },
    ];
  },
};

export default nextConfig;
