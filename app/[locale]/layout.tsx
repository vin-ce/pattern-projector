import "./globals.css";

import { NextIntlClientProvider } from "next-intl";
import { getMessages } from "next-intl/server";

import type { Metadata, Viewport } from "next";

const APP_TITLE = "Pattern Projector";
const APP_DESCRIPTION =
  "Calibrates projectors for projecting sewing patterns with accurate scaling and without perspective distortion";
const APP_URL = "https://www.patternprojector.com/";

export const metadata: Metadata = {
  metadataBase: new URL(APP_URL),
  description: "Calibrate your projector for sewing patterns",
  applicationName: APP_TITLE,
  title: APP_TITLE,
  manifest: "/manifest.json",
  appleWebApp: {
    capable: true,
    statusBarStyle: "default",
    title: APP_TITLE,
    // startUpImage: [],
  },
  formatDetection: {
    telephone: false,
  },
  openGraph: {
    type: "website",
    siteName: APP_TITLE,
    title: APP_TITLE,
    description: APP_DESCRIPTION,
    url: APP_URL,
  },
  twitter: {
    card: "summary",
    title: APP_TITLE,
    description: APP_DESCRIPTION,
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  minimumScale: 1,
  maximumScale: 1,
  userScalable: false,
  themeColor: "#000",
};

export default async function LocaleLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const messages = await getMessages({ locale });

  return (
    <html lang={locale}>
      <body
        style={{
          overscrollBehavior: "none",
          overflow: "hidden",
          height: "100vh",
          paddingTop: "env(safe-area-inset-top)",
        }}
      >
        <NextIntlClientProvider locale={locale} messages={messages}>
          {children}
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
