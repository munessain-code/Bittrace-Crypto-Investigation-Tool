import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "BitTrace — Graph Explorer",
  description: "AI-powered Bitcoin fraud forensics on Elliptic++",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full overflow-hidden">
      <body className="h-full overflow-hidden">
        {children}
      </body>
    </html>
  );
}
