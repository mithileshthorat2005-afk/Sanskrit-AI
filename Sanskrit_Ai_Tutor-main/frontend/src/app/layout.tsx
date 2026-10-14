import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/context/AuthContext";

export const metadata: Metadata = {
  title: "SanskritaAI | Divine Language Architecture",
  description: "Experience the convergence of ancient wisdom and modern artificial intelligence. Learn Sanskrit with adaptive AI-powered lessons, grammar analysis, and interactive games.",
  keywords: "Sanskrit, learn Sanskrit, AI tutor, language learning, Devanagari, grammar",
  authors: [{ name: "SanskritaAI" }],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        {/* The Google jsapi loader + `google.load("elements", ..., "transliteration")`
            block was removed: the Google Elements API it drives was retired, the
            loader could never have run (a synchronously-parsed inline script always
            executed before the async `jsapi` request returned), and nothing in the
            app referenced `google.transliterate`. Roman→Devanagari handling lives in
            `@/components/SanskritInput` and `@/lib`, and IAST rendering uses
            `@indic-transliteration/sanscript`, both bundled locally. */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Marcellus&family=Outfit:wght@300;400;600;800&family=Noto+Sans+Devanagari:wght@400;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
