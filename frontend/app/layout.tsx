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
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap"
          rel="stylesheet"
        />
      </head>
      <body style={{ height: "100%", display: "flex", flexDirection: "column", overflow: "hidden", margin: 0 }}>
        {children}
      </body>
    </html>
  );
}
