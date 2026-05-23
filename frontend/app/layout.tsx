import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SIREN — Incident Response Engine",
  description: "Self-Improving Incident Response Engine · Autonomous AI agent",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" style={{ height: "100%" }}>
      <head>
        <link
          href="https://fonts.googleapis.com/css2?family=Geist:wght@400;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body style={{ margin: 0, padding: 0 }}>
        {children}
      </body>
    </html>
  );
}
