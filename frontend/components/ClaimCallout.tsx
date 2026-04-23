"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { useSession, signIn, signOut } from "next-auth/react";
import { fetchMe } from "@/lib/api";

interface ClaimCalloutProps {
  moeCode: string;
  schoolShortName: string;
  schoolEmail: string | null;
  isClaimed: boolean;
}

/**
 * Renders a callout on unclaimed school pages inviting the HM to sign in
 * with the school's @moe.edu.my Google Workspace account to claim it.
 *
 * Renders nothing when the school is already claimed OR when the viewer
 * is already the school's admin. If the viewer is signed in as a different
 * Google account, shows a different message explaining they need to sign
 * in with the school's MOE address.
 */
export default function ClaimCallout({
  moeCode,
  schoolShortName,
  schoolEmail,
  isClaimed,
}: ClaimCalloutProps) {
  const t = useTranslations("claim");
  const { data: session } = useSession();
  const [viewerIsAdmin, setViewerIsAdmin] = useState(false);
  const [viewerEmail, setViewerEmail] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!session) return;
    fetchMe().then((me) => {
      if (!me) return;
      setViewerEmail(me.email);
      if (me.admin_school?.moe_code === moeCode) {
        setViewerIsAdmin(true);
      }
    });
  }, [session, moeCode]);

  if (isClaimed) return null;
  if (viewerIsAdmin) return null;
  if (!schoolEmail) return null;

  const shareUrl = typeof window !== "undefined"
    ? window.location.href
    : `https://tamilschool.org/en/school/${moeCode}`;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(shareUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // fallback: no-op
    }
  };

  return (
    <div className="my-4 rounded-lg border border-blue-200 bg-blue-50 p-4 text-sm text-blue-900">
      <div className="flex items-start gap-3">
        <svg className="w-5 h-5 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <div className="flex-1 space-y-3">
          <p className="font-medium">{t("unclaimedHeading")}</p>

          {!session && (
            <>
              <p>
                {t("hmPrompt", { school: schoolShortName, email: schoolEmail })}
              </p>
              <button
                onClick={() => signIn("google")}
                className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700"
              >
                {t("signInToClaim")}
              </button>
            </>
          )}

          {session && viewerEmail && (
            <>
              <p>
                {t("wrongAccount", { viewer: viewerEmail, expected: schoolEmail })}
              </p>
              <button
                onClick={() => signOut()}
                className="inline-flex items-center gap-2 px-4 py-2 bg-white border border-blue-300 text-blue-700 text-sm font-medium rounded-lg hover:bg-blue-100"
              >
                {t("signOut")}
              </button>
            </>
          )}

          <p className="text-xs text-blue-700 pt-2 border-t border-blue-200">
            {t("alertHmPrompt")}{" "}
            <button
              onClick={handleCopy}
              className="underline font-medium hover:text-blue-900"
            >
              {copied ? t("copied") : t("copyLink")}
            </button>
          </p>
        </div>
      </div>
    </div>
  );
}
