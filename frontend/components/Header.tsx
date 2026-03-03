"use client";

import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { useState } from "react";
import LanguageSwitcher from "./LanguageSwitcher";

export default function Header() {
  const t = useTranslations("header");
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <header className="bg-white shadow-sm border-b border-gray-200 relative z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <Link href="/" className="flex items-center gap-2">
            <span className="text-xl font-bold text-primary-700">
              {t("title")}
            </span>
          </Link>

          <nav className="hidden md:flex items-center gap-6">
            <Link
              href="/"
              className="text-sm font-medium text-gray-700 hover:text-primary-600"
            >
              {t("schoolMap")}
            </Link>
            <Link
              href="/constituencies"
              className="text-sm font-medium text-gray-700 hover:text-primary-600"
            >
              {t("constituencies")}
            </Link>
            <Link
              href="/news"
              className="text-sm font-medium text-gray-700 hover:text-primary-600"
            >
              {t("newsReports")}
            </Link>
            <Link
              href="/about"
              className="text-sm font-medium text-gray-700 hover:text-primary-600"
            >
              {t("about")}
            </Link>
            <Link
              href="/contact"
              className="text-sm font-medium text-gray-700 hover:text-primary-600"
            >
              {t("contact")}
            </Link>
            <LanguageSwitcher />
          </nav>

          <button
            className="md:hidden p-2 text-gray-600 hover:text-gray-900"
            onClick={() => setMenuOpen(!menuOpen)}
            aria-label={t("toggleMenu")}
          >
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              {menuOpen ? (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              ) : (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              )}
            </svg>
          </button>
        </div>
      </div>

      {menuOpen && (
        <div className="md:hidden bg-white border-t border-gray-200 py-2">
          <Link
            href="/"
            className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
            onClick={() => setMenuOpen(false)}
          >
            {t("schoolMap")}
          </Link>
          <Link
            href="/constituencies"
            className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
            onClick={() => setMenuOpen(false)}
          >
            {t("constituencies")}
          </Link>
          <Link
            href="/news"
            className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
            onClick={() => setMenuOpen(false)}
          >
            {t("newsReports")}
          </Link>
          <Link
            href="/about"
            className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
            onClick={() => setMenuOpen(false)}
          >
            {t("about")}
          </Link>
          <Link
            href="/contact"
            className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
            onClick={() => setMenuOpen(false)}
          >
            {t("contact")}
          </Link>
          <div className="px-4 py-2">
            <LanguageSwitcher />
          </div>
        </div>
      )}
    </header>
  );
}
