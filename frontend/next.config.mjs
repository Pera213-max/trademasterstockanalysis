/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  output: 'standalone',
  // Privacy: Remove X-Powered-By header
  poweredByHeader: false,
  // Privacy: Disable source maps in production
  productionBrowserSourceMaps: false,
  // Privacy: Remove build ID from public assets
  generateBuildId: async () => {
    return 'build';
  },
};

export default nextConfig;
