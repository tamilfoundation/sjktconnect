"use client";

import { useEffect, useState } from "react";
import { useTranslations, useLocale } from "next-intl";
import { useSession, signIn, signOut } from "next-auth/react";
import { fetchMe } from "@/lib/api";

interface EmailClaimIndicatorProps {
  moeCode: string;
  schoolEmail: string;
  isClaimed: boolean;
  claimedAt: string | null;
  lastVerified: string | null;
}

/**
 * Inline indicator that sits next to the school's email in the School Details
 * card. Small, subtle — matches Google Business "Own this business?" pattern.
 *
 * States:
 * - Claimed: green "Verified" pill (clickable for claim/verify dates).
 * - Unclaimed + signed out: "Claim this page →" text link → opens modal.
 * - Unclaimed + signed in with different account: "Claim this page" link →
 *   opens modal explaining wrong-account situation.
 * - Unclaimed + signed in as admin of this school: impossible (would have
 *   auto-claimed on sign-in). Defensive: render nothing.
 */
export default function EmailClaimIndicator({
  moeCode,
  schoolEmail,
  isClaimed,
  claimedAt,
  lastVerified,
}: EmailClaimIndicatorProps) {
  const t = useTranslations("claim");
  const locale = useLocale();
  const { data: session } = useSession();
  const [viewerEmail, setViewerEmail] = useState<string | null>(null);
  const [viewerIsAdmin, setViewerIsAdmin] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [showTooltip, setShowTooltip] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!session) {
      setViewerEmail(null);
      setViewerIsAdmin(false);
      return;
    }
    fetchMe().then((me) => {
      if (!me) return;
      setViewerEmail(me.email);
      if (me.admin_school?.moe_code === moeCode) setViewerIsAdmin(true);
    });
  }, [session, moeCode]);

  const fmt = (iso: string) =>
    new Intl.DateTimeFormat(locale, { year: "numeric", month: "long", day: "numeric" })
      .format(new Date(iso));

  const handleCopy = async () => {
    try {
      const url = typeof window !== "undefined"
        ? window.location.href
        : `https://tamilschool.org/en/school/${moeCode}`;
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch { /* no-op */ }
  };

  // CLAIMED — small verified pill
  if (isClaimed && claimedAt) {
    return (
      <>
        <button
          type="button"
          onClick={() => setShowTooltip((o) => !o)}
          className="ml-2 inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-green-50 text-green-700 text-xs font-medium hover:bg-green-100 transition align-middle"
          aria-label={t("verified")}
        >
          <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
          </svg>
          {t("verified")}
        </button>
        {showTooltip && (
          <div className="absolute z-10 mt-1 w-64 p-3 rounded-lg bg-white border border-gray-200 shadow-lg text-xs text-gray-700">
            <p className="mb-1"><span className="font-medium">{t("claimedOn")}</span> {fmt(claimedAt)}</p>
            {lastVerified && (
              <p><span className="font-medium">{t("verifiedOn")}</span> {fmt(lastVerified)}</p>
            )}
          </div>
        )}
      </>
    );
  }

  // UNCLAIMED
  if (viewerIsAdmin) return null; // shouldn't happen; defensive

  return (
    <>
      <button
        type="button"
        onClick={() => setShowModal(true)}
        className="ml-2 text-xs text-blue-600 hover:text-blue-800 underline align-middle"
      >
        {t("claimShort")}
      </button>

      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={() => setShowModal(false)}>
          <div
            className="bg-white rounded-xl shadow-xl max-w-md w-full"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
              <h2 className="text-base font-semibold text-gray-900">{t("claimModalTitle")}</h2>
              <button onClick={() => setShowModal(false)} className="text-gray-400 hover:text-gray-600">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="p-6 space-y-4 text-sm text-gray-700">
              {!session ? (
                <>
                  <p>{t("hmPrompt", { school: "", email: schoolEmail })}</p>
                  <button
                    onClick={() => signIn("google")}
                    className="w-full inline-flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700"
                  >
                    {t("signInToClaim")}
                  </button>
                </>
              ) : (
                <>
                  <p>{t("wrongAccount", { viewer: viewerEmail ?? "", expected: schoolEmail })}</p>
                  <button
                    onClick={() => signOut()}
                    className="w-full inline-flex items-center justify-center gap-2 px-4 py-2 bg-white border border-gray-300 text-gray-800 text-sm font-medium rounded-lg hover:bg-gray-50"
                  >
                    {t("signOut")}
                  </button>
                </>
              )}

              <div className="text-xs text-gray-500 pt-3 border-t border-gray-100">
                <p className="mb-2">{t("alertHmPrompt")}</p>
                <button
                  onClick={handleCopy}
                  className="text-blue-600 hover:text-blue-800 underline"
                >
                  {copied ? t("copied") : t("copyLink")}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
