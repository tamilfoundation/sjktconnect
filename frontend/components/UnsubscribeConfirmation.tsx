"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { unsubscribe } from "@/lib/api";

interface UnsubscribeConfirmationProps {
  token: string;
}

export default function UnsubscribeConfirmation({ token }: UnsubscribeConfirmationProps) {
  const t = useTranslations("subscribe");
  const tc = useTranslations("common");
  const [loading, setLoading] = useState(true);
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    async function doUnsubscribe() {
      try {
        const result = await unsubscribe(token);
        setEmail(result.email);
      } catch (err) {
        setError(err instanceof Error ? err.message : tc("somethingWrong"));
      } finally {
        setLoading(false);
      }
    }
    doUnsubscribe();
  }, [token, tc]);

  if (loading) {
    return (
      <div className="text-center py-8">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-gray-100 mb-4 animate-pulse">
          <svg className="w-8 h-8 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <p className="text-gray-600">{t("processing")}</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-8">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-red-100 mb-4">
          <svg className="w-8 h-8 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </div>
        <h2 className="text-xl font-semibold text-gray-900 mb-2">{t("unableTo")}</h2>
        <p className="text-gray-600">{error}</p>
        <p className="text-sm text-gray-500 mt-4">
          {t("linkExpired")}
        </p>
      </div>
    );
  }

  return (
    <div className="text-center py-8">
      <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-green-100 mb-4">
        <svg className="w-8 h-8 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
        </svg>
      </div>
      <h2 className="text-xl font-semibold text-gray-900 mb-2">{t("unsubscribed")}</h2>
      <p className="text-gray-600">
        <strong>{email}</strong> {t("removedFrom")}
      </p>
      <p className="text-sm text-gray-500 mt-4">
        {t("changedMind")}{" "}
        <Link href="/subscribe" className="text-primary-600 hover:text-primary-700 underline">
          {t("resubscribe")}
        </Link>
      </p>
    </div>
  );
}
