import type { Metadata } from "next";

import "./globals.css";
import { QueryProvider } from "./query-provider";

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
      <body>
        <QueryProvider>{children}</QueryProvider>
      </body>
    </html>
  );
}
