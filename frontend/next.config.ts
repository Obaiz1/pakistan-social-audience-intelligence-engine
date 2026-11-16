import type { NextConfig } from "next";

// Local development proxies /api/v1/* to the FastAPI dev server; on Vercel, vercel.json routes it to the Python function.
// Pattern from Repo B (signalspend-ai frontend/next.config.ts).
const config: NextConfig = {
  devIndicators: false,
  poweredByHeader: false,
  async rewrites() {
    if (process.env.VERCEL) return [];
    return [{ source: "/api/v1/:path*", destination: `${process.env.API_ORIGIN || "http://127.0.0.1:8000"}/api/v1/:path*` }];
  },
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "same-origin" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
        ],
      },
    ];
  },
};
export default config;
