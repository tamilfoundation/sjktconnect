"use client";

import { useState, useRef, useEffect } from "react";
import { useSession, signIn, signOut } from "next-auth/react";
import { logoutDjangoSession } from "@/lib/auth-api";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { syncGoogleAuth, type UserProfile } from "@/lib/auth-api";
import { emitProfileReady } from "@/lib/auth-events";

export default function UserMenu() {
  const t = useTranslations("auth");
  const { data: session, status } = useSession();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Sync with backend when session is available. After the Django session
  // cookie is set, broadcast "profile ready" so other auth-aware components
  // (EditSchoolLink, SuggestButton) can re-fetch — their first fetchMe
  // racing this POST is exactly why CTAs needed a manual refresh after
  // sign-in (TD-18).
  useEffect(() => {
    if (session && (session as any).id_token && !profile) {
      syncGoogleAuth((session as any).id_token)
        .then((p) => {
          setProfile(p);
          emitProfileReady();
        })
        .catch(() => {});
    }
  }, [session, profile]);

  // Close on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  if (status === "loading") return null;

  if (!session) {
    return (
      <button
        onClick={() => signIn("google")}
        className="text-sm font-medium text-gray-700 hover:text-primary-600 transition-colors"
      >
        {t("signIn")}
      </button>
    );
  }

  const avatarUrl = profile?.avatar_url || session.user?.image || "";
  const displayName = profile?.display_name || session.user?.name || "";
  const role = profile?.role || "USER";
  const pendingCount = profile?.pending_moderation_count ?? 0;

  return (
    <div className="relative" ref={menuRef}>
      <button
        onClick={() => setOpen(!open)}
        className="relative flex items-center gap-2 text-sm"
        aria-label={pendingCount > 0 ? `${pendingCount} pending review` : "Account menu"}
      >
        {avatarUrl ? (
          <img
            src={avatarUrl}
            alt=""
            className="w-8 h-8 rounded-full border border-gray-200"
            referrerPolicy="no-referrer"
          />
        ) : (
          <div className="w-8 h-8 rounded-full bg-primary-100 flex items-center justify-center text-primary-700 font-medium">
            {displayName.charAt(0).toUpperCase()}
          </div>
        )}
        {pendingCount > 0 && (
          <span
            className="absolute -top-1 -right-1 min-w-[18px] h-[18px] px-1 rounded-full bg-red-600 text-white text-[11px] font-semibold leading-[18px] text-center border-2 border-white"
            aria-hidden="true"
          >
            {pendingCount > 99 ? "99+" : pendingCount}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-56 bg-white rounded-xl border border-gray-200 shadow-lg py-2 z-50">
          <div className="px-4 py-2 border-b border-gray-100">
            <p className="text-sm font-medium text-gray-900 truncate">{displayName}</p>
            <p className="text-xs text-gray-500">{t(`role_${role}`)}</p>
            {profile?.points !== undefined && profile.points > 0 && (
              <p className="text-xs text-primary-600 mt-0.5">
                {profile.points} {t("points")}
              </p>
            )}
          </div>
          <Link
            href="/profile"
            className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
            onClick={() => setOpen(false)}
          >
            {t("profile")}
          </Link>
          {pendingCount > 0 && (
            <Link
              href="/dashboard/suggestions"
              className="flex items-center justify-between px-4 py-2 text-sm font-medium text-red-700 bg-red-50 hover:bg-red-100"
              onClick={() => setOpen(false)}
            >
              <span>{t("reviewPending")}</span>
              <span className="inline-flex items-center justify-center min-w-[20px] h-[20px] px-1.5 rounded-full bg-red-600 text-white text-[11px] font-semibold">
                {pendingCount > 99 ? "99+" : pendingCount}
              </span>
            </Link>
          )}
          {(role === "MODERATOR" || role === "SUPERADMIN" || profile?.admin_school) && (
            <Link
              href="/dashboard"
              className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
              onClick={() => setOpen(false)}
            >
              {t("dashboard")}
            </Link>
          )}
          {role === "SUPERADMIN" && (
            <Link
              href="/dashboard/users"
              className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
              onClick={() => setOpen(false)}
            >
              {t("userManagement")}
            </Link>
          )}
          <button
            onClick={async () => {
              // Clear the Django session BEFORE the JWT so fetchMe() starts
              // returning null immediately for admin-gated UI elsewhere on
              // the page. Otherwise EditSchoolLink + ImageManager links
              // outlive the sign-out (Sprint 15 hotfix).
              await logoutDjangoSession();
              signOut();
            }}
            className="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-gray-50"
          >
            {t("signOut")}
          </button>
        </div>
      )}
    </div>
  );
}
