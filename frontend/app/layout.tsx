import type { Metadata } from "next";
import "./globals.css";
import { Sidebar } from "@/components/Sidebar";
import { QueryProvider } from "@/components/QueryProvider";

export const metadata: Metadata = {
  title: "eye-budget",
  description: "Receipt OCR and budget management",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <QueryProvider>
          <div className="flex min-h-screen">
            <Sidebar />
            <main className="flex-1 ml-56 p-8 overflow-y-auto flex flex-col h-screen">{children}</main>
          </div>
        </QueryProvider>
      </body>
    </html>
  );
}
