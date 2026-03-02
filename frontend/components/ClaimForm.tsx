"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { requestMagicLink } from "@/lib/api";

interface ClaimFormProps {
  moeCode?: string;
}

export default function ClaimForm({ moeCode }: ClaimFormProps) {
  const t = useTranslations("claim");
  const tc = useTranslations("common");
  const [email, setEmail] = useState(moeCode ? `${moeCode.toLowerCase()}@moe.edu.my` : "");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [schoolName, setSchoolName] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const result = await requestMagicLink(email);
      setSchoolName(result.school_name);
      setSent(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : tc("somethingWrong"));
    } finally {
      setLoading(false);
    }
  }

  if (sent) {
    return (
      <div className="text-center py-8">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-green-100 mb-4">
          <svg className="w-8 h-8 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
          </svg>
        </div>
        <h2 className="text-xl font-semibold text-gray-900 mb-2">{t("checkEmail")}</h2>
        <p className="text-gray-600 mb-1">
          {t("sentVerification")} <strong>{email}</strong>
        </p>
        <p className="text-gray-600 mb-4">
          {t("for")} <strong>{schoolName}</strong>.
        </p>
        <p className="text-sm text-gray-500">
          {t("linkExpires")}
        </p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
          {t("schoolEmail")}
        </label>
        <input
          type="email"
          id="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder={t("emailPlaceholder")}
          required
          className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
        />
        <p className="mt-1 text-sm text-gray-500">
          {t("moeOnly")}
        </p>
      </div>

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
          {error}
        </div>
      )}

      <button
        type="submit"
        disabled={loading}
        className="w-full bg-primary-600 text-white font-medium px-6 py-3 rounded-lg hover:bg-primary-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {loading ? t("sending") : t("sendVerification")}
      </button>
    </form>
  );
}
