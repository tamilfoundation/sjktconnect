"use client";

import { useState, useRef, useEffect } from "react";
import { useSession, signIn, signOut } from "next-auth/react";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { syncGoogleAuth, type UserProfile } from "@/lib/auth-api";

export default function UserMenu() {
  const t = useTranslations("auth");
  const { data: session, status } = useSession();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Sync with backend when session is available
  useEffect(() => {
    if (session && (session as any).id_token && !profile) {
      syncGoogleAuth((session as any).id_token)
        .then(setProfile)
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

  return (
    <div className="relative" ref={menuRef}>
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 text-sm"
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
          {(role === "MODERATOR" || role === "SUPERADMIN" || profile?.admin_school) && (
            <Link
              href="/dashboard"
              className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
              onClick={() => setOpen(false)}
            >
              {t("dashboard")}
            </Link>
          )}
          <button
            onClick={() => signOut()}
            className="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-gray-50"
          >
            {t("signOut")}
          </button>
        </div>
      )}
    </div>
  );
}
