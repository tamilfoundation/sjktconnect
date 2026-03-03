const createNextIntlPlugin = require("next-intl/plugin");

const withNextIntl = createNextIntlPlugin("./i18n/request.ts");

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  typescript: {
    // Next.js 14 auto-generated .next/types files use bare React.ReactNode
    // which TypeScript 5.9+ can't resolve. Type-checking done via tsc separately.
    ignoreBuildErrors: true,
  },
};

module.exports = withNextIntl(nextConfig);
