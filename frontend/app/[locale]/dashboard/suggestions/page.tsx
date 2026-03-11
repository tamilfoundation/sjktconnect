"use client";

import { useSession } from "next-auth/react";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import ModerationQueue from "@/components/ModerationQueue";

export default function ModerationQueuePage() {
  const t = useTranslations("suggestions");
  const { status } = useSession();

  if (status === "loading") {
    return (
      <div className="max-w-4xl mx-auto px-4 py-16 text-center text-gray-500">
        Loading...
      </div>
    );
  }

  if (status !== "authenticated") {
    return (
      <div className="max-w-4xl mx-auto px-4 py-16 text-center">
        <p className="text-gray-600 mb-4">Please sign in to access this page.</p>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="flex items-center gap-2 text-sm text-gray-500 mb-6">
        <Link href="/dashboard" className="hover:text-gray-700">
          Dashboard
        </Link>
        <span>/</span>
        <span className="text-gray-900">{t("moderationQueue")}</span>
      </div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">
        {t("moderationQueue")}
      </h1>
      <ModerationQueue />
    </div>
  );
}
