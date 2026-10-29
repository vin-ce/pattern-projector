import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
import withSerwistInit from "@serwist/next";
import createNextIntlPlugin from "next-intl/plugin";

const withSerwist = withSerwistInit({
  swSrc: "app/sw.ts",
  swDest: "public/sw.js",
  reloadOnOnline: true,
  disable: process.env.NODE_ENV === "development",
});

const withNextIntl = createNextIntlPlugin("./i18n.ts");

/** @type {import('next').NextConfig} */
const nextConfig = {
  webpack: (config) => {
    // The minified distribution avoids nested webpack export-scope collisions in Next dev.
    config.resolve.alias["pdfjs-dist$"] = require.resolve(
      "pdfjs-dist/build/pdf.min.mjs",
    );
    config.resolve.alias.canvas = false;
    config.resolve.fallback = { fs: false };
    return config;
  },
};

export default withNextIntl(withSerwist(nextConfig));
