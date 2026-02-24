import type { Metadata } from "next";
import "./globals.css";
import Sidebar from "@/components/Sidebar";

export const metadata: Metadata = {
    title: "Research Catalyst — AI Research Paper Assistance Platform",
    description:
        "An intelligent, unified research assistance platform supporting the complete research lifecycle — from problem formulation and literature discovery to writing, visualization, review, and publication.",
};

export default function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    return (
        <html lang="en">
            <body>
                <div className="app-layout">
                    <Sidebar />
                    <main className="main-content">{children}</main>
                </div>
            </body>
        </html>
    );
}
