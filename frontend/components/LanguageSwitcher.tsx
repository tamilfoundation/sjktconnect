"use client";

import { useLocale } from "next-intl";
import { usePathname, useRouter } from "@/i18n/navigation";
import { routing } from "@/i18n/routing";

const localeLabels: Record<string, string> = {
  en: "EN",
  ta: "தமிழ்",
  ms: "BM",
};

export default function LanguageSwitcher() {
  const locale = useLocale();
  const pathname = usePathname();
  const router = useRouter();

  function onLocaleChange(newLocale: string) {
    router.replace(pathname, { locale: newLocale });
  }

  return (
    <div className="flex items-center gap-1 text-sm">
      {routing.locales.map((l, i) => (
        <span key={l}>
          {i > 0 && <span className="text-gray-300 mx-1">|</span>}
          <button
            onClick={() => onLocaleChange(l)}
            className={`hover:text-primary-600 ${
              locale === l
                ? "font-bold text-primary-700 underline underline-offset-4"
                : "text-gray-500"
            }`}
          >
            {localeLabels[l]}
          </button>
        </span>
      ))}
    </div>
  );
}
