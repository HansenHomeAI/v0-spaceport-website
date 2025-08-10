/** @type {import('next').NextConfig} */
const basePath = process.env.NEXT_PUBLIC_BASE_PATH || '';
const nextConfig = {
  reactStrictMode: true,
  experimental: { appDir: true },
  images: { unoptimized: true },
  // SSR/ISR via Cloudflare Pages Functions (no static export)
  basePath,
  assetPrefix: basePath ? `${basePath}/` : undefined,
};
module.exports = nextConfig;
