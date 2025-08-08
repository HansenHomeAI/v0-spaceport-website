/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  experimental: { appDir: true },
  images: { unoptimized: true },
  async redirects() {
    return [
      { source: '/', destination: '/landing', permanent: false },
    ];
  },
};
module.exports = nextConfig;
