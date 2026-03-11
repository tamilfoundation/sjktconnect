"use client";

import { useState } from "react";
import { useSession } from "next-auth/react";
import { useTranslations } from "next-intl";
import SuggestForm from "@/components/SuggestForm";

interface SuggestButtonProps {
  moeCode: string;
}

export default function SuggestButton({ moeCode }: SuggestButtonProps) {
  const t = useTranslations("suggestions");
  const { data: session } = useSession();
  const [showForm, setShowForm] = useState(false);

  if (!session) return null;

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
