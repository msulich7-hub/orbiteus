/** @type {import('next').NextConfig} */
const path = require("node:path");

const nextConfig = {
  /** Allow admin UI dev/HMR when opened via VM IP (not only localhost). */
  allowedDevOrigins: [
    "10.10.99.60",
    "localhost",
    "127.0.0.1",
  ],
  /**
   * npm workspaces hoist `next` to the repo root. Point Turbopack there so
   * `next/package.json` resolves; paths still resolve under this app’s `src/`.
   */
  turbopack: {
    root: path.join(__dirname, ".."),
  },
};

module.exports = nextConfig;
