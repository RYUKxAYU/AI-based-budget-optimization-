import type { Metadata } from "next";
import "./globals.css";
import Navbar from "@/components/layout/Navbar";

export const metadata: Metadata = {
  title: "AI Green Budget Optimizer",
  description: "AI-driven AQI forecasting and green budget optimization for Indian cities",
  keywords: ["AQI", "green budget", "AI", "environment", "India", "optimization"],
  authors: [{ name: "AI Green Budget Team" }],
  openGraph: {
    title: "AI Green Budget Optimizer",
    description: "Optimize environmental spending with AI-driven AQI forecasting",
    type: "website",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="bg-navy min-h-screen">
        <Navbar />
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {children}
        </main>
      </body>
    </html>
  );
}
