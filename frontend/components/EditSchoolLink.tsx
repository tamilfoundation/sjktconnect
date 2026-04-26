"use client";

import { useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { fetchMe } from "@/lib/api";
import { onProfileReady } from "@/lib/auth-events";

interface EditSchoolLinkProps {
  moeCode: string;
}

export default function EditSchoolLink({ moeCode }: EditSchoolLinkProps) {
  const t = useTranslations("parliamentWatch");
  const { status } = useSession();
  const [canEdit, setCanEdit] = useState(false);

  useEffect(() => {
    // Reset on sign-out / unknown so the button hides immediately without
    // a hard refresh. On sign-in, fetchMe races UserMenu's syncGoogleAuth
    // POST that sets the Django session cookie — so we (a) try once now,
    // (b) re-try on the auth-events "profile ready" signal that fires
    // after syncGoogleAuth resolves. This is what closes TD-18: previously
    // the first fetch returned null and the button stayed hidden until
    // the next page load. Re-querying on the explicit signal removes the
    // race without polling.
    if (status !== "authenticated") {
      setCanEdit(false);
      return;
    }
    let cancelled = false;
    const load = () => {
      fetchMe()
        .then((user) => {
          if (cancelled || !user) return;
          const isSuper = user.role === "SUPERADMIN";
          const isAdmin = user.admin_school?.moe_code === moeCode;
          if (isSuper || isAdmin) setCanEdit(true);
        })
        .catch(() => { /* keep hidden on error */ });
    };
    load();
    const unsub = onProfileReady(load);
    return () => { cancelled = true; unsub(); };
  }, [moeCode, status]);

  if (!canEdit) return null;

  return (
    <Link
      href={`/school/${moeCode}/edit`}
      className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700"
    >
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
      </svg>
      {t("editSchoolData")}
    </Link>
  );
}
