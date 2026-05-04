/** @type {import('next').NextConfig} */
const path = require("node:path");

const nextConfig = {
  /**
   * npm workspaces hoist `next` to the repo root. Point Turbopack there so
   * `next/package.json` resolves; paths still resolve under this app’s `src/`.
   */
  turbopack: {
    root: path.join(__dirname, ".."),
  },
};

module.exports = nextConfig;
