"use client";

import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";

interface HeroSectionProps {
  totalSchools: number;
  states: number;
  constituencies: number;
}

export default function HeroSection({
  totalSchools,
  states,
  constituencies,
}: HeroSectionProps) {
  const t = useTranslations("hero");

  const handleScrollToMap = () => {
    const mapEl = document.getElementById("school-map");
    if (mapEl) {
      mapEl.scrollIntoView({ behavior: "smooth" });
    }
  };

  return (
    <section className="bg-gradient-to-br from-blue-950 via-blue-900 to-indigo-900 text-white">
      <div className="max-w-7xl mx-auto px-4 py-12 sm:py-16 lg:py-20">
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-8 lg:gap-12 items-center">
          {/* Left: headline + CTAs */}
          <div className="lg:col-span-3">
            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold leading-tight">
              {t("headline")}
            </h1>
            <p className="text-xl sm:text-2xl lg:text-3xl font-light text-blue-200 mt-2">
              {t("subheadline")}
            </p>
            <p className="text-base sm:text-lg text-blue-100 mt-4 max-w-2xl">
              {t("description")}
            </p>
            <div className="mt-8 flex flex-wrap gap-4">
              <button
                onClick={handleScrollToMap}
                className="inline-flex items-center gap-2 px-6 py-3 bg-white text-blue-900 font-semibold rounded-lg hover:bg-blue-50 transition-colors"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  className="h-5 w-5"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2}
                  aria-hidden="true"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M21 21l-4.35-4.35m0 0A7 7 0 1 0 6.65 16.65 7 7 0 0 0 16.65 16.65z"
                  />
                </svg>
                {t("findSchool")}
              </button>
              <Link
                href="/subscribe"
                className="px-6 py-3 border-2 border-white text-white font-semibold rounded-lg hover:bg-white/10 transition-colors"
              >
                {t("subscribeIntel")}
              </Link>
            </div>
          </div>

          {/* Right: asymmetric stat cards */}
          <div className="lg:col-span-2 flex flex-col gap-4">
            {/* Large prominent card — Schools */}
            <div className="bg-white/10 backdrop-blur-md border border-white/20 rounded-xl p-6 text-center">
              <div className="text-5xl sm:text-6xl font-bold">
                {totalSchools.toLocaleString()}
              </div>
              <div className="text-base text-blue-200 mt-2">{t("schoolsLabel")}</div>
            </div>

            {/* Two smaller cards stacked side by side */}
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-white/10 backdrop-blur-md border border-white/20 rounded-xl p-4 text-center">
                <div className="text-3xl sm:text-4xl font-bold">
                  {states.toLocaleString()}
                </div>
                <div className="text-sm text-blue-200 mt-1">{t("statesLabel")}</div>
              </div>
              <div className="bg-white/10 backdrop-blur-md border border-white/20 rounded-xl p-4 text-center">
                <div className="text-3xl sm:text-4xl font-bold">
                  {constituencies.toLocaleString()}
                </div>
                <div className="text-sm text-blue-200 mt-1">
                  {t("constituenciesLabel")}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
