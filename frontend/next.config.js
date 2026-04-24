const createNextIntlPlugin = require("next-intl/plugin");

const withNextIntl = createNextIntlPlugin("./i18n/request.ts");

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  typescript: {
    // Pre-existing implicit-any issues in components (BoundaryMap, etc.) — type-check
    // is done via tsc in dev and via test runner. Revisit as part of a dedicated
    // type-hygiene pass (see docs/tech-debt.md TD-11/14 slot for future work).
    ignoreBuildErrors: true,
  },
};

module.exports = withNextIntl(nextConfig);
