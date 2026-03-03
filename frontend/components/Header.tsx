"use client";

import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import React, { useState, useEffect, useRef, useCallback } from "react";
import LanguageSwitcher from "./LanguageSwitcher";

/* ------------------------------------------------------------------ */
/*  Data-driven navigation config                                      */
/* ------------------------------------------------------------------ */

const NAV_GROUPS = [
  {
    id: "explore",
    labelKey: "exploreLabel",
    items: [
      { labelKey: "schoolMap", descKey: "schoolMapDesc", href: "/" },
      {
        labelKey: "constituencies",
        descKey: "constituenciesDesc",
        href: "/constituencies",
      },
      {
        labelKey: "aboutTamilSchools",
        descKey: "aboutTamilSchoolsDesc",
        href: "/about-tamil-schools",
      },
    ],
  },
  {
    id: "intelligence",
    labelKey: "intelligenceLabel",
    items: [
      { labelKey: "newsReports", descKey: "newsReportsDesc", href: "/news" },
      { labelKey: "issues", descKey: "issuesDesc", href: "/issues" },
      {
        labelKey: "parliamentWatch",
        descKey: "parliamentWatchDesc",
        href: "/parliament-watch",
      },
    ],
  },
  {
    id: "resources",
    labelKey: "resourcesLabel",
    items: [
      {
        labelKey: "ptaToolkit",
        descKey: "ptaToolkitDesc",
        href: "/resources/pta-toolkit",
      },
      {
        labelKey: "lpsToolkit",
        descKey: "lpsToolkitDesc",
        href: "/resources/lps-toolkit",
      },
      {
        labelKey: "dataDownloads",
        descKey: "dataDownloadsDesc",
        href: "/data",
      },
      { labelKey: "faq", descKey: "faqDesc", href: "/faq" },
    ],
  },
  {
    id: "about",
    labelKey: "aboutLabel",
    items: [
      { labelKey: "about", descKey: "aboutDesc", href: "/about" },
      { labelKey: "contact", descKey: "contactDesc", href: "/contact" },
    ],
  },
] as const;

/* ------------------------------------------------------------------ */
/*  Chevron icon (small, inline)                                       */
/* ------------------------------------------------------------------ */

function ChevronDown({ open }: { open: boolean }) {
  return (
    <svg
      className={`ml-1 h-4 w-4 transition-transform ${open ? "rotate-180" : ""}`}
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      aria-hidden="true"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M19 9l-7 7-7-7"
      />
    </svg>
  );
}

/* ------------------------------------------------------------------ */
/*  Header component                                                   */
/* ------------------------------------------------------------------ */

export default function Header() {
  const t = useTranslations("header");

  /* ---- state ---- */
  const [menuOpen, setMenuOpen] = useState(false); // mobile menu
  const [activeGroup, setActiveGroup] = useState<string | null>(null); // desktop dropdown
  const [expandedMobileGroup, setExpandedMobileGroup] = useState<string | null>(
    null,
  ); // mobile accordion

  /* ---- refs ---- */
  const navRef = useRef<HTMLElement>(null);
  const dropdownItemsRef = useRef<(HTMLDivElement | null)[]>([]);

  /* ---- close on outside click ---- */
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (navRef.current && !navRef.current.contains(e.target as Node)) {
        setActiveGroup(null);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  /* ---- close on Escape ---- */
  useEffect(() => {
    function handleEscape(e: KeyboardEvent) {
      if (e.key === "Escape") {
        setActiveGroup(null);
        setMenuOpen(false);
      }
    }
    document.addEventListener("keydown", handleEscape);
    return () => document.removeEventListener("keydown", handleEscape);
  }, []);

  /* ---- close mobile menu when viewport hits md breakpoint ---- */
  useEffect(() => {
    const mq = window.matchMedia("(min-width: 768px)");
    function handleChange(e: MediaQueryListEvent | MediaQueryList) {
      if (e.matches) {
        setMenuOpen(false);
        setExpandedMobileGroup(null);
      }
    }
    handleChange(mq); // initial check
    mq.addEventListener("change", handleChange);
    return () => mq.removeEventListener("change", handleChange);
  }, []);

  /* ---- toggle desktop dropdown ---- */
  const toggleGroup = useCallback((groupId: string) => {
    setActiveGroup((prev) => (prev === groupId ? null : groupId));
  }, []);

  /* ---- toggle mobile accordion ---- */
  const toggleMobileGroup = useCallback((groupId: string) => {
    setExpandedMobileGroup((prev) => (prev === groupId ? null : groupId));
  }, []);

  /* ---- keyboard navigation within dropdown ---- */
  const handleDropdownKeyDown = useCallback(
    (e: React.KeyboardEvent, groupId: string) => {
      const group = NAV_GROUPS.find((g) => g.id === groupId);
      if (!group) return;

      const items = dropdownItemsRef.current.filter(Boolean);
      const currentIndex = items.indexOf(
        document.activeElement as HTMLDivElement,
      );

      if (e.key === "ArrowDown") {
        e.preventDefault();
        const next = currentIndex + 1 < items.length ? currentIndex + 1 : 0;
        items[next]?.focus();
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        const prev =
          currentIndex - 1 >= 0 ? currentIndex - 1 : items.length - 1;
        items[prev]?.focus();
      } else if (e.key === "Escape") {
        setActiveGroup(null);
      }
    },
    [],
  );

  /* ---- close helpers ---- */
  const closeDesktop = useCallback(() => setActiveGroup(null), []);
  const closeMobile = useCallback(() => {
    setMenuOpen(false);
    setExpandedMobileGroup(null);
  }, []);

  /* ================================================================ */
  /*  Render                                                           */
  /* ================================================================ */

  return (
    <>
      {/* Skip-to-content link */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:z-[100] focus:bg-white focus:px-4 focus:py-2 focus:text-blue-600"
      >
        Skip to content
      </a>

      <header className="bg-white shadow-sm border-b border-gray-200 relative z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            {/* ---- Logo ---- */}
            <Link href="/" className="flex items-center gap-2">
              <span className="text-xl font-bold text-primary-700">
                {t("title")}
              </span>
            </Link>

            {/* ============================================ */}
            {/*  Desktop navigation                          */}
            {/* ============================================ */}
            <nav
              ref={navRef}
              className="hidden md:flex items-center gap-1"
              aria-label="Main navigation"
            >
              {NAV_GROUPS.map((group) => {
                const isOpen = activeGroup === group.id;

                return (
                  <div key={group.id} className="relative">
                    {/* Group trigger */}
                    <button
                      type="button"
                      onClick={() => toggleGroup(group.id)}
                      onKeyDown={(e) => {
                        if (e.key === "ArrowDown" && isOpen) {
                          e.preventDefault();
                          dropdownItemsRef.current[0]?.focus();
                        }
                      }}
                      className={`inline-flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                        isOpen
                          ? "text-primary-600 bg-primary-50"
                          : "text-gray-700 hover:text-primary-600 hover:bg-gray-50"
                      }`}
                      aria-expanded={isOpen}
                      aria-haspopup="true"
                    >
                      {t(group.labelKey)}
                      <ChevronDown open={isOpen} />
                    </button>

                    {/* Dropdown panel */}
                    {isOpen && (
                      <div
                        role="menu"
                        className="absolute left-0 mt-2 w-64 bg-white rounded-lg shadow-lg border border-gray-200 py-2"
                        onKeyDown={(e) => handleDropdownKeyDown(e, group.id)}
                      >
                        {group.items.map((item, idx) => (
                          <div
                            key={item.href}
                            role="menuitem"
                            tabIndex={-1}
                            ref={(el) => {
                              dropdownItemsRef.current[idx] = el;
                            }}
                            className="focus:bg-gray-50 focus:outline-none"
                            onKeyDown={(e) => {
                              if (e.key === "Enter" || e.key === " ") {
                                e.preventDefault();
                                (
                                  e.currentTarget.querySelector(
                                    "a",
                                  ) as HTMLAnchorElement
                                )?.click();
                              }
                            }}
                          >
                            <Link
                              href={item.href}
                              className="block px-4 py-3 hover:bg-gray-50"
                              onClick={closeDesktop}
                              tabIndex={-1}
                            >
                              <span className="block font-medium text-gray-900">
                                {t(item.labelKey)}
                              </span>
                              <span className="block text-xs text-gray-500 mt-0.5">
                                {t(item.descKey)}
                              </span>
                            </Link>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}

              {/* Language switcher */}
              <div className="ml-2">
                <LanguageSwitcher />
              </div>

              {/* CTA buttons */}
              <Link
                href="/subscribe"
                className="ml-2 px-4 py-2 text-sm font-medium border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50 transition-colors"
              >
                {t("subscribe")}
              </Link>
              <Link
                href="/donate"
                className="ml-1 px-4 py-2 text-sm font-medium bg-amber-500 text-white rounded-md hover:bg-amber-600 transition-colors"
              >
                {t("donate")}
              </Link>
            </nav>

            {/* ---- Hamburger button (mobile) ---- */}
            <button
              className="md:hidden p-2 text-gray-600 hover:text-gray-900"
              onClick={() => setMenuOpen(!menuOpen)}
              aria-label={t("toggleMenu")}
              aria-expanded={menuOpen}
            >
              <svg
                className="w-6 h-6"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                {menuOpen ? (
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12"
                  />
                ) : (
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 6h16M4 12h16M4 18h16"
                  />
                )}
              </svg>
            </button>
          </div>
        </div>

        {/* ============================================ */}
        {/*  Mobile menu (accordion)                     */}
        {/* ============================================ */}
        {menuOpen && (
          <div className="md:hidden bg-white border-t border-gray-200">
            <nav aria-label="Mobile navigation">
              {NAV_GROUPS.map((group) => {
                const isExpanded = expandedMobileGroup === group.id;

                return (
                  <div
                    key={group.id}
                    className="border-b border-gray-100 last:border-b-0"
                  >
                    {/* Accordion trigger */}
                    <button
                      type="button"
                      onClick={() => toggleMobileGroup(group.id)}
                      className="flex w-full items-center justify-between px-4 py-3 text-sm font-medium text-gray-700 hover:bg-gray-50"
                      aria-expanded={isExpanded}
                    >
                      {t(group.labelKey)}
                      <ChevronDown open={isExpanded} />
                    </button>

                    {/* Accordion content */}
                    {isExpanded && (
                      <div className="bg-gray-50 pb-1">
                        {group.items.map((item) => (
                          <Link
                            key={item.href}
                            href={item.href}
                            className="block px-8 py-2.5 text-sm text-gray-600 hover:text-primary-600 hover:bg-gray-100"
                            onClick={closeMobile}
                          >
                            {t(item.labelKey)}
                          </Link>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}

              {/* Language switcher */}
              <div className="px-4 py-3 border-t border-gray-100">
                <LanguageSwitcher />
              </div>

              {/* CTA buttons */}
              <div className="px-4 py-3 space-y-2">
                <Link
                  href="/subscribe"
                  className="block w-full text-center px-4 py-2 text-sm font-medium border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50 transition-colors"
                  onClick={closeMobile}
                >
                  {t("subscribe")}
                </Link>
                <Link
                  href="/donate"
                  className="block w-full text-center px-4 py-2 text-sm font-medium bg-amber-500 text-white rounded-md hover:bg-amber-600 transition-colors"
                  onClick={closeMobile}
                >
                  {t("donate")}
                </Link>
              </div>
            </nav>
          </div>
        )}
      </header>
    </>
  );
}
