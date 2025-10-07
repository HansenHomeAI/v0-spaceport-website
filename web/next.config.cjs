const path = require('path');
const fs = require('fs');
const dotenv = require('dotenv');
const webpack = require('webpack');
const { withSentryConfig } = require('@sentry/nextjs');

// Load local env files for dev, supporting both web/ and repo root locations
// This lets NEXT_PUBLIC_GOOGLE_MAPS_API_KEY work locally without relying on CF Pages
const loadIfExists = (filePath) => {
  if (fs.existsSync(filePath)) {
    dotenv.config({ path: filePath });
  }
};
const repoRoot = path.join(__dirname, '..');
loadIfExists(path.join(__dirname, '.env.local'));
loadIfExists(path.join(__dirname, '.env'));
loadIfExists(path.join(repoRoot, '.env.local'));
loadIfExists(path.join(repoRoot, '.env'));

/** @type {import('next').NextConfig} */
const basePath = process.env.NEXT_PUBLIC_BASE_PATH || '';
const nextConfig = {
  reactStrictMode: true,
  experimental: { appDir: true },
  images: { unoptimized: true },
  // Do not use static export; we deploy with @cloudflare/next-on-pages to enable Pages Functions.
  basePath,
  assetPrefix: basePath ? `${basePath}/` : undefined,
  // Ensure client code receives the key in dev by falling back to GOOGLE_MAPS_API_KEY
  env: {
    NEXT_PUBLIC_GOOGLE_MAPS_API_KEY:
      process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY || process.env.GOOGLE_MAPS_API_KEY || '',
  },
  webpack: (config) => {
    config.plugins = config.plugins || [];

    const cesiumBaseUrl = `${basePath || ''}/cesium`;

    config.plugins.push(
      new webpack.DefinePlugin({
        CESIUM_BASE_URL: JSON.stringify(cesiumBaseUrl),
      }),
      new webpack.NormalModuleReplacementPlugin(
        /^@zip\.js\/zip\.js\/lib\/zip-no-worker\.js$/,
        path.join(__dirname, 'lib/zip-no-worker.js')
      )
    );

    config.resolve = config.resolve || {};
    config.resolve.alias = {
      ...(config.resolve.alias || {}),
      '@zip.js/zip.js/lib/zip-no-worker.js$': path.join(__dirname, 'lib/zip-no-worker.js'),
    };
    config.resolve.fallback = {
      ...(config.resolve.fallback || {}),
      fs: false,
      path: false,
    };

    return config;
  },
};

// Sentry configuration
const sentryWebpackPluginOptions = {
  // Additional config options for the Sentry webpack plugin. Keep in mind that
  // the following options are set automatically, and overriding them is not
  // recommended:
  //   release, url, configFile, stripPrefix, urlPrefix, include, ignore

  org: process.env.SENTRY_ORG,
  project: process.env.SENTRY_PROJECT,

  // An optional authentication token for Sentry.
  // Note: This is required for uploading source maps to Sentry.
  authToken: process.env.SENTRY_AUTH_TOKEN,

  // For all available options, see:
  // https://github.com/getsentry/sentry-webpack-plugin#options

  // Suppresses source map uploading logs during build
  silent: true,
  // For all available options, see:
  // https://docs.sentry.io/platforms/javascript/guides/nextjs/manual-setup/

  // Upload a larger set of source maps for prettier stack traces (increases build time)
  widenClientFileUpload: true,

  // Transpiles SDK to be compatible with IE11 (increases bundle size)
  transpileClientSDK: true,

  // Routes browser requests to Sentry through a Next.js rewrite to circumvent ad-blockers (increases server load)
  tunnelRoute: "/monitoring",

  // Hides source maps from generated client bundles
  hideSourceMaps: true,

  // Automatically tree-shake Sentry logger statements to reduce bundle size
  disableLogger: true,

  // Enables automatic instrumentation of Vercel Cron Monitors. (Does not yet work with App Router route handlers.)
  // See: https://docs.sentry.io/product/crons/
  // automaticVercelMonitors: true,
};

module.exports = withSentryConfig(nextConfig, sentryWebpackPluginOptions);
