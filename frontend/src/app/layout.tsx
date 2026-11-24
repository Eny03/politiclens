import type { Metadata, Viewport } from "next";
import localFont from "next/font/local";
import "./globals.css";
import { Navbar } from "@/components/Navbar";
import { Footer } from "@/components/Footer";
import { InstallAppBanner } from "@/components/InstallAppBanner";

const geistSans = localFont({
  src: "./fonts/GeistVF.woff",
  variable: "--font-geist-sans",
  weight: "100 900",
});
const geistMono = localFont({
  src: "./fonts/GeistMonoVF.woff",
  variable: "--font-geist-mono",
  weight: "100 900",
});

export const metadata: Metadata = {
  title: "PoliticLens | Analizzatore e Comparatore Politico Autonomo",
  description: "Piattaforma autonoma e neutrale di monitoraggio delle posizioni politiche italiane, manifesto dinamico comparabile e fact-checking finanziario.",
  manifest: "/manifest.json",
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "PoliticLens",
  },
  icons: {
    icon: "/icon.svg",
    apple: "/icon.svg",
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
  viewportFit: "cover",
  themeColor: "#0f172a",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="it">
      <head>
        <link rel="icon" href="/icon.svg" type="image/svg+xml" />
        <link rel="apple-touch-icon" href="/icon.svg" />
      </head>
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased min-h-screen text-slate-900 dark:text-slate-100 flex flex-col overflow-x-hidden w-full max-w-full`}
      >
        <Navbar />
        <InstallAppBanner />
        <main className="flex-1 w-full max-w-full min-w-0 overflow-x-hidden">{children}</main>
        <Footer />
      </body>
    </html>
  );
}
