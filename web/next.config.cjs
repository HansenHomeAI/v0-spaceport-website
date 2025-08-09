/** @type {import('next').NextConfig} */
const basePath = process.env.NEXT_PUBLIC_BASE_PATH || '';
const output = process.env.NEXT_OUTPUT_EXPORT ? 'export' : undefined;
const nextConfig = {
  reactStrictMode: true,
  experimental: { appDir: true },
  images: { unoptimized: true },
  output,
  basePath,
  assetPrefix: basePath ? `${basePath}/` : undefined,
};
module.exports = nextConfig;
