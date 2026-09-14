import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SAT-SA | SOC Supervisory Analytics Tool",
  description: "Prototype supervisory analytics for SOC assessment using synthetic operational evidence.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        {children}
      </body>
    </html>
  );
}
