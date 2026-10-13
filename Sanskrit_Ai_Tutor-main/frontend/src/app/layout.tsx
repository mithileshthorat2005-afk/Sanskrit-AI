import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/context/AuthContext";
import SupportChat from "@/components/SupportChat";

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
        <script src="https://www.google.com/jsapi" async defer></script>
        <script
          dangerouslySetInnerHTML={{
            __html: `
              if (window.google && google.load) {
                google.load("elements", "1", {
                  packages: "transliteration"
                });
              }
            `,
          }}
        />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Marcellus&family=Outfit:wght@300;400;600;800&family=Noto+Sans+Devanagari:wght@400;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>
        <AuthProvider>
          {children}
          <SupportChat />
        </AuthProvider>
      </body>
    </html>
  );
}
