import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "Agentic Resume Trace",
  description: "Agent run trace viewer for Agentic Resume.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
