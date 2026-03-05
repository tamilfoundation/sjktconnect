"use client";

import { useTranslations } from "next-intl";
import { MPProfile } from "@/lib/types";

interface ContactMPCardProps {
  mp: MPProfile | null;
  constituencyCode: string;
  constituencyName: string;
}

export default function ContactMPCard({
  mp,
  constituencyCode,
  constituencyName,
}: ContactMPCardProps) {
  const t = useTranslations("constituency");

  if (!mp) return null;

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-2 px-6 py-4 border-b border-gray-100">
        <div className="w-1 h-5 bg-amber-600 rounded-full" />
        <h2 className="text-lg font-semibold text-gray-800">
          {t("contactYourMP")}
        </h2>
      </div>

      <div className="px-6 py-5 space-y-5">
        {/* Photo + Name */}
        <div className="text-center">
          <div className="relative inline-block mb-3">
            {mp.photo_url ? (
              <img
                src={mp.photo_url}
                alt={mp.name}
                className="w-24 h-24 rounded-full object-cover border-2 border-gray-200"
              />
            ) : (
              <div className="w-24 h-24 rounded-full bg-gray-100 flex items-center justify-center text-2xl font-bold text-gray-400">
                {mp.name.charAt(0)}
              </div>
            )}
            {mp.party && (
              <span className="absolute -bottom-1 -right-1 bg-gray-800 text-white text-xs font-bold px-2 py-0.5 rounded-full">
                {mp.party}
              </span>
            )}
          </div>
          <p className="font-semibold text-gray-900 text-base">{mp.name}</p>
          <p className="text-sm text-gray-500 mt-0.5">
            {constituencyName} · {constituencyCode}
          </p>
        </div>

        {/* Action buttons */}
        <div className="space-y-2">
          {mp.email && (
            <a
              href={`mailto:${mp.email}`}
              aria-label={t("emailMP")}
              className="flex items-center justify-center gap-2 w-full py-3 bg-amber-700 hover:bg-amber-800 text-white font-semibold text-sm rounded-lg transition-colors"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M21.75 6.75v10.5a2.25 2.25 0 01-2.25 2.25h-15a2.25 2.25 0 01-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0019.5 4.5h-15a2.25 2.25 0 00-2.25 2.25m19.5 0v.243a2.25 2.25 0 01-1.07 1.916l-7.5 4.615a2.25 2.25 0 01-2.36 0L3.32 8.91a2.25 2.25 0 01-1.07-1.916V6.75" />
              </svg>
              {t("emailMP")}
            </a>
          )}

          {mp.phone && (
            <a
              href={`tel:${mp.phone}`}
              aria-label={t("callServiceCentre")}
              className="flex items-center justify-center gap-2 w-full py-2.5 bg-white border border-amber-700 text-amber-700 hover:bg-amber-50 font-medium text-sm rounded-lg transition-colors"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 6.75c0 8.284 6.716 15 15 15h2.25a2.25 2.25 0 002.25-2.25v-1.372c0-.516-.351-.966-.852-1.091l-4.423-1.106c-.44-.11-.902.055-1.173.417l-.97 1.293c-.282.376-.769.542-1.21.38a12.035 12.035 0 01-7.143-7.143c-.162-.441.004-.928.38-1.21l1.293-.97c.363-.271.527-.734.417-1.173L6.963 3.102a1.125 1.125 0 00-1.091-.852H4.5A2.25 2.25 0 002.25 4.5v2.25z" />
              </svg>
              {t("callServiceCentre")}
            </a>
          )}

          {mp.facebook_url && (
            <a
              href={mp.facebook_url}
              target="_blank"
              rel="noopener noreferrer"
              aria-label="Facebook"
              className="flex items-center justify-center gap-2 w-full py-2.5 bg-[#1877F2] hover:bg-[#166FE5] text-white font-medium text-sm rounded-lg transition-colors"
            >
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z" />
              </svg>
              Facebook
            </a>
          )}
        </div>

        {/* Service centre address */}
        {mp.service_centre_address && (
          <div className="flex gap-2 text-xs text-gray-500">
            <svg className="w-3.5 h-3.5 mt-0.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M15 10.5a3 3 0 11-6 0 3 3 0 016 0z" />
              <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1115 0z" />
            </svg>
            <span>{mp.service_centre_address}</span>
          </div>
        )}

        {/* External links */}
        <div className="flex justify-center gap-4 pt-2 border-t border-gray-100 text-xs text-gray-400">
          {mp.parlimen_profile_url && (
            <a
              href={mp.parlimen_profile_url}
              target="_blank"
              rel="noopener noreferrer"
              aria-label={t("parliamentProfile")}
              className="hover:text-gray-600 transition-colors"
            >
              {t("parliamentProfile")} →
            </a>
          )}
          {mp.mymp_profile_url && (
            <a
              href={mp.mymp_profile_url}
              target="_blank"
              rel="noopener noreferrer"
              aria-label={t("mympProfile")}
              className="hover:text-gray-600 transition-colors"
            >
              {t("mympProfile")} →
            </a>
          )}
        </div>
      </div>
    </div>
  );
}
