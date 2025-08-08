/** @type {import('next').NextConfig} */
const basePath = process.env.NEXT_PUBLIC_BASE_PATH || '';
const nextConfig = {
  reactStrictMode: true,
  experimental: { appDir: true },
  images: { unoptimized: true },
  basePath,
  assetPrefix: basePath ? `${basePath}/` : undefined,
};
module.exports = nextConfig;
