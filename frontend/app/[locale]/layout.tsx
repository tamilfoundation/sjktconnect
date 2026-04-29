import type { Metadata } from "next";
import "../globals.css";
import { NextIntlClientProvider } from "next-intl";
import { getMessages, setRequestLocale } from "next-intl/server";
import { notFound } from "next/navigation";
import { routing } from "@/i18n/routing";
import Header from "@/components/Header";
import Footer from "@/components/Footer";
import AuthProvider from "@/components/AuthProvider";
import { buildAlternates } from "@/lib/seo";

// Sprint 21: tell Next.js about the known locale set so it can
// statically generate the layout shell per locale (paired with
// setRequestLocale below for full static-render support).
export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await params;
  return {
    title: "SJK(T) Connect — Tamil School Intelligence Platform",
    description:
      "Interactive map and data platform for Malaysia's 528 Tamil schools. Track parliamentary mentions, MP scorecards, and school data.",
    icons: {
      icon: [
        { url: "/favicon.ico", sizes: "any" },
        { url: "/icon.svg", type: "image/svg+xml" },
      ],
      apple: "/apple-touch-icon.png",
    },
    alternates: buildAlternates("/", locale as "en" | "ta" | "ms"),
  };
}

export default async function LocaleLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;

  if (!routing.locales.includes(locale as any)) {
    notFound();
  }

  // Sprint 21: enable static rendering by telling next-intl the locale
  // is known from URL params (not from headers/cookies). Without this,
  // getMessages() reads requestLocale via cookies/headers, which marks
  // the layout as dynamic and forces every page below it to render
  // dynamically — overriding `revalidate = 86400` on every page.
  // Cache-Control header was 'no-cache, no-store' as a result;
  // Cloudflare wouldn't cache; bots forced fresh renders every hit.
  setRequestLocale(locale);

  const messages = await getMessages();

  return (
    <html lang={locale}>
      <body className="flex flex-col min-h-screen bg-gray-50">
        <NextIntlClientProvider messages={messages}>
          <AuthProvider>
            <Header />
            <main id="main-content" className="flex-1">{children}</main>
            <Footer />
          </AuthProvider>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
