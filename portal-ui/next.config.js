/** @type {import('next').NextConfig} */
const path = require("node:path");

const nextConfig = {
  /**
   * npm workspaces hoist `next` to the repo root; Turbopack needs that root.
   */
  turbopack: {
    root: path.join(__dirname, ".."),
  },
  async rewrites() {
    const backendUrl = process.env.BACKEND_URL || "http://localhost:8000";
    return [
      // Portal traffic flows through the dedicated /api/portal/* surface (PR 12),
      // not the admin /api/* (ADR-0007).
      {
        source: "/api/:path*",
        destination: `${backendUrl}/api/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
