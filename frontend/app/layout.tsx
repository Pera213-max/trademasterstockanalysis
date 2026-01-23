import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "./providers";

const defaultDescription =
  "Data-driven stock analysis for Finnish and US markets with real-time data and technical insights.";

export const viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export const metadata: Metadata = {
  title: {
    default: "OsakedataX",
    template: "%s | OsakedataX",
  },
  description: defaultDescription,
  icons: {
    icon: "/favicon.ico",
    apple: "/apple-touch-icon.png",
  },
  manifest: "/site.webmanifest",
  themeColor: "#0b1120",
  openGraph: {
    title: "OsakedataX",
    description: defaultDescription,
    type: "website",
    images: [
      {
        url: "/icon-512.png",
        width: 512,
        height: 512,
        alt: "OsakedataX",
      },
    ],
  },
  twitter: {
    card: "summary",
    title: "OsakedataX",
    description: defaultDescription,
    images: ["/icon-512.png"],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <link rel="icon" href="/favicon.ico" sizes="any" />
        <link rel="apple-touch-icon" href="/apple-touch-icon.png" />
        <link rel="manifest" href="/site.webmanifest" />
        <script async src="https://plausible.io/js/pa-Z4OQWxyi3JBVpzvGgLS3Q.js"></script>
        <script
          dangerouslySetInnerHTML={{
            __html:
              "window.plausible=window.plausible||function(){(plausible.q=plausible.q||[]).push(arguments)},plausible.init=plausible.init||function(i){plausible.o=i||{}};plausible.init();",
          }}
        />
      </head>
      <body className="antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
