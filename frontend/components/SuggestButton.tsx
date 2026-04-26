"use client";

import { useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import { useTranslations } from "next-intl";
import { fetchMe } from "@/lib/api";
import { onProfileReady } from "@/lib/auth-events";
import SuggestForm from "@/components/SuggestForm";

interface SuggestButtonProps {
  moeCode: string;
}

/**
 * Suggest-an-edit CTA. Visible to authenticated users who CANNOT directly
 * edit this school:
 *   * SUPERADMIN — hidden (use Edit School Data instead)
 *   * Bound admin of this school — hidden (use Edit School Data instead)
 *   * Bound admin of a different school — visible (suggest, don't edit)
 *   * MODERATOR / regular USER — visible
 *   * Signed-out — hidden (must sign in to suggest)
 */
export default function SuggestButton({ moeCode }: SuggestButtonProps) {
  const t = useTranslations("suggestions");
  const { status } = useSession();
  const [canSuggest, setCanSuggest] = useState(false);
  const [showForm, setShowForm] = useState(false);

  useEffect(() => {
    if (status !== "authenticated") {
      setCanSuggest(false);
      return;
    }
    let cancelled = false;
    const load = () => {
      fetchMe()
        .then((user) => {
          if (cancelled || !user) return;
          const isSuper = user.role === "SUPERADMIN";
          const isAdminOfThis = user.admin_school?.moe_code === moeCode;
          // Suggest is for users who can't edit directly. Hide for the two
          // roles that already get the Edit button.
          setCanSuggest(!isSuper && !isAdminOfThis);
        })
        .catch(() => setCanSuggest(false));
    };
    // Try once immediately; re-fetch on the auth-events "profile ready"
    // signal (fired by UserMenu after syncGoogleAuth resolves) to close
    // the race where the first fetch lands before the Django session
    // cookie does. TD-18.
    load();
    const unsub = onProfileReady(load);
    return () => { cancelled = true; unsub(); };
  }, [moeCode, status]);

  if (!canSuggest) return null;

  return (
    <>
      <button
        onClick={() => setShowForm(true)}
        className="inline-flex items-center gap-2 px-4 py-2 bg-amber-500 text-white text-sm font-medium rounded-lg hover:bg-amber-600 transition-colors"
      >
        <svg
          className="w-4 h-4"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 20h9M16.5 3.5a2.121 2.121 0 113 3L7 19l-4 1 1-4L16.5 3.5z"
          />
        </svg>
        {t("suggestEdit")}
      </button>

      {showForm && (
        <SuggestForm moeCode={moeCode} onClose={() => setShowForm(false)} />
      )}
    </>
  );
}
