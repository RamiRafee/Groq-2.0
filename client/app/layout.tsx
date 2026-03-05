import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AgentUI",
  description: "Conversational AI agent with web search",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}