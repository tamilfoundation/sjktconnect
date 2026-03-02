"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { subscribe } from "@/lib/api";

export default function SubscribeForm() {
  const t = useTranslations("subscribe");
  const tc = useTranslations("common");
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [organisation, setOrganisation] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  const CATEGORIES = [
    {
      key: "PARLIAMENT_WATCH",
      label: t("parliamentWatch"),
      description: t("parliamentDesc"),
    },
    {
      key: "NEWS_WATCH",
      label: t("newsWatch"),
      description: t("newsDesc"),
    },
    {
      key: "MONTHLY_BLAST",
      label: t("monthlyBlast"),
      description: t("monthlyDesc"),
    },
  ];

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      await subscribe({ email, name, organisation });
      setSuccess(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : tc("somethingWrong"));
    } finally {
      setLoading(false);
    }
  }

  if (success) {
    return (
      <div className="text-center py-8">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-green-100 mb-4">
          <svg className="w-8 h-8 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <h2 className="text-xl font-semibold text-gray-900 mb-2">{t("youreSubscribed")}</h2>
        <p className="text-gray-600 mb-1">
          {t("confirmSent")} <strong>{email}</strong>.
        </p>
        <p className="text-sm text-gray-500 mt-4">
          {t("manageNote")}
        </p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label htmlFor="subscribe-email" className="block text-sm font-medium text-gray-700 mb-1">
          {t("emailLabel")} <span className="text-red-500">*</span>
        </label>
        <input
          type="email"
          id="subscribe-email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder={t("emailPlaceholder")}
          required
          className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
        />
      </div>

      <div>
        <label htmlFor="subscribe-name" className="block text-sm font-medium text-gray-700 mb-1">
          {t("nameLabel")}
        </label>
        <input
          type="text"
          id="subscribe-name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder={t("namePlaceholder")}
          className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
        />
      </div>

      <div>
        <label htmlFor="subscribe-org" className="block text-sm font-medium text-gray-700 mb-1">
          {t("orgLabel")}
        </label>
        <input
          type="text"
          id="subscribe-org"
          value={organisation}
          onChange={(e) => setOrganisation(e.target.value)}
          placeholder={t("orgPlaceholder")}
          className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
        />
      </div>

      <div>
        <p className="text-sm font-medium text-gray-700 mb-2">
          {t("updatesOn")}
        </p>
        <div className="space-y-2">
          {CATEGORIES.map((cat) => (
            <div key={cat.key} className="flex items-start gap-2 p-2 bg-gray-50 rounded">
              <svg className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              <div>
                <span className="text-sm font-medium text-gray-900">{cat.label}</span>
                <p className="text-xs text-gray-500">{cat.description}</p>
              </div>
            </div>
          ))}
        </div>
        <p className="text-xs text-gray-500 mt-2">
          {t("allEnabled")}
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
        {loading ? t("subscribing") : t("subscribeButton")}
      </button>
    </form>
  );
}
