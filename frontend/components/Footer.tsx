"use client";

import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";

export default function Footer() {
  const t = useTranslations("footer");

  return (
    <footer className="bg-gray-900 text-gray-400">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        <div className="grid grid-cols-2 md:grid-cols-5 gap-8">
          {/* Column 1: Brand */}
          <div className="col-span-2 md:col-span-1">
            <p className="text-white font-semibold text-sm mb-2">
              SJK(T) Connect
            </p>
            <p className="text-xs leading-relaxed">
              {t("copyright", { year: new Date().getFullYear() })}
            </p>
            <p className="text-xs text-gray-500 mt-1">
              {t("dataLastUpdated")}
            </p>

            {/* Social media icons */}
            <div className="flex items-center gap-3 mt-4">
              <a
                href="https://www.facebook.com/tamilfoundation"
                target="_blank"
                rel="noopener noreferrer"
                className="text-gray-500 hover:text-white transition-colors"
                aria-label="Facebook"
              >
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z" />
                </svg>
              </a>
              <a
                href="https://x.com/taborgtf"
                target="_blank"
                rel="noopener noreferrer"
                className="text-gray-500 hover:text-white transition-colors"
                aria-label="X (Twitter)"
              >
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
                </svg>
              </a>
            </div>
          </div>

          {/* Column 2: Explore */}
          <div>
            <h3 className="text-white text-xs font-semibold uppercase tracking-wider mb-3">
              {t("exploreTitle")}
            </h3>
            <ul className="space-y-2">
              <li>
                <Link href="/" className="text-xs hover:text-white transition-colors">
                  {t("schoolMap")}
                </Link>
              </li>
              <li>
                <Link href="/constituencies" className="text-xs hover:text-white transition-colors">
                  {t("constituencies")}
                </Link>
              </li>
              <li>
                <Link href="/about-tamil-schools" className="text-xs hover:text-white transition-colors">
                  {t("aboutTamilSchools")}
                </Link>
              </li>
            </ul>
          </div>

          {/* Column 3: Intelligence */}
          <div>
            <h3 className="text-white text-xs font-semibold uppercase tracking-wider mb-3">
              {t("intelligenceTitle")}
            </h3>
            <ul className="space-y-2">
              <li>
                <Link href="/news" className="text-xs hover:text-white transition-colors">
                  {t("newsReports")}
                </Link>
              </li>
              <li>
                <Link href="/issues" className="text-xs hover:text-white transition-colors">
                  {t("issues")}
                </Link>
              </li>
              <li>
                <Link href="/parliament-watch" className="text-xs hover:text-white transition-colors">
                  {t("parliamentWatch")}
                </Link>
              </li>
            </ul>
          </div>

          {/* Column 4: Resources */}
          <div>
            <h3 className="text-white text-xs font-semibold uppercase tracking-wider mb-3">
              {t("resourcesTitle")}
            </h3>
            <ul className="space-y-2">
              <li>
                <Link href="/resources/pta-toolkit" className="text-xs hover:text-white transition-colors">
                  {t("ptaToolkit")}
                </Link>
              </li>
              <li>
                <Link href="/resources/lps-toolkit" className="text-xs hover:text-white transition-colors">
                  {t("lpsToolkit")}
                </Link>
              </li>
              <li>
                <Link href="/data" className="text-xs hover:text-white transition-colors">
                  {t("dataDownloads")}
                </Link>
              </li>
              <li>
                <Link href="/faq" className="text-xs hover:text-white transition-colors">
                  {t("faq")}
                </Link>
              </li>
            </ul>
          </div>

          {/* Column 5: About & Legal */}
          <div>
            <h3 className="text-white text-xs font-semibold uppercase tracking-wider mb-3">
              {t("aboutTitle")}
            </h3>
            <ul className="space-y-2">
              <li>
                <Link href="/about" className="text-xs hover:text-white transition-colors">
                  {t("about")}
                </Link>
              </li>
              <li>
                <Link href="/contact" className="text-xs hover:text-white transition-colors">
                  {t("contact")}
                </Link>
              </li>
              <li>
                <Link href="/subscribe" className="text-xs hover:text-white transition-colors">
                  {t("subscribe")}
                </Link>
              </li>
              <li>
                <Link href="/donate" className="text-xs hover:text-white transition-colors">
                  {t("donate")}
                </Link>
              </li>
            </ul>
            <ul className="space-y-2 mt-4 pt-4 border-t border-gray-800">
              <li>
                <Link href="/privacy" className="text-xs hover:text-white transition-colors">
                  {t("privacyPolicy")}
                </Link>
              </li>
              <li>
                <Link href="/terms" className="text-xs hover:text-white transition-colors">
                  {t("termsOfService")}
                </Link>
              </li>
              <li>
                <Link href="/cookies" className="text-xs hover:text-white transition-colors">
                  {t("cookiePolicy")}
                </Link>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </footer>
  );
}
