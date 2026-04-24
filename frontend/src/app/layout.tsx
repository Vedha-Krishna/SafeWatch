import type { Metadata } from "next";
import "../index.css";

export const metadata: Metadata = {
  title: "SafeWatch",
  description: "Frontend connected to FastAPI incident API",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
