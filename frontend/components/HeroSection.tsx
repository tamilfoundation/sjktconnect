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
    <section className="bg-blue-900 text-white">
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
                className="px-6 py-3 bg-white text-blue-900 font-semibold rounded-lg hover:bg-blue-50 transition-colors"
              >
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

          {/* Right: stat cards */}
          <div className="lg:col-span-2 grid grid-cols-3 gap-4">
            <StatCard value={totalSchools} label={t("schoolsLabel")} />
            <StatCard value={states} label={t("statesLabel")} />
            <StatCard value={constituencies} label={t("constituenciesLabel")} />
          </div>
        </div>
      </div>
    </section>
  );
}

function StatCard({ value, label }: { value: number; label: string }) {
  return (
    <div className="bg-blue-800/50 rounded-lg p-4 text-center">
      <div className="text-3xl sm:text-4xl font-bold">{value.toLocaleString()}</div>
      <div className="text-sm text-blue-200 mt-1">{label}</div>
    </div>
  );
}
