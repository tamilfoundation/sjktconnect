"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { fetchPreferences, updatePreferences } from "@/lib/api";

interface PreferencesFormProps {
  token: string;
}

export default function PreferencesForm({ token }: PreferencesFormProps) {
  const t = useTranslations("subscribe");
  const tc = useTranslations("common");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  const [email, setEmail] = useState("");
  const [preferences, setPreferences] = useState<Record<string, boolean>>({});

  const CATEGORY_LABELS: Record<string, { label: string; description: string }> = {
    PARLIAMENT_WATCH: {
      label: t("parliamentWatch"),
      description: t("parliamentDesc"),
    },
    NEWS_WATCH: {
      label: t("newsWatch"),
      description: t("newsDesc"),
    },
    MONTHLY_BLAST: {
      label: t("monthlyBlast"),
      description: t("monthlyDescAlt"),
    },
  };

  useEffect(() => {
    async function loadPreferences() {
      try {
        const data = await fetchPreferences(token);
        setEmail(data.email);
        setPreferences(data.preferences);
      } catch (err) {
        setError(err instanceof Error ? err.message : tc("somethingWrong"));
      } finally {
        setLoading(false);
      }
    }
    loadPreferences();
  }, [token, tc]);

  function handleToggle(category: string) {
    setPreferences((prev) => ({
      ...prev,
      [category]: !prev[category],
    }));
    setSaved(false);
  }

  async function handleSave() {
    setError("");
    setSaving(true);
    setSaved(false);

    try {
      const data = await updatePreferences(token, preferences);
      setPreferences(data.preferences);
      setSaved(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : tc("somethingWrong"));
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="text-center py-8">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-gray-100 mb-4 animate-pulse">
          <svg className="w-8 h-8 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <p className="text-gray-600">{t("loadingPrefs")}</p>
      </div>
    );
  }

  if (error && !email) {
    return (
      <div className="text-center py-8">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-red-100 mb-4">
          <svg className="w-8 h-8 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </div>
        <h2 className="text-xl font-semibold text-gray-900 mb-2">{t("unableToLoad")}</h2>
        <p className="text-gray-600">{error}</p>
        <p className="text-sm text-gray-500 mt-4">
          {t("prefLinkExpired")}
        </p>
      </div>
    );
  }

  return (
    <div>
      <p className="text-sm text-gray-500 mb-4">
        {t("managingFor")} <strong>{email}</strong>
      </p>

      <div className="space-y-3">
        {Object.entries(CATEGORY_LABELS).map(([key, { label, description }]) => (
          <label
            key={key}
            className="flex items-start gap-3 p-3 border rounded-lg cursor-pointer hover:bg-gray-50 transition-colors"
          >
            <input
              type="checkbox"
              checked={preferences[key] ?? true}
              onChange={() => handleToggle(key)}
              className="mt-1 h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
            />
            <div>
              <span className="text-sm font-medium text-gray-900">{label}</span>
              <p className="text-xs text-gray-500">{description}</p>
            </div>
          </label>
        ))}
      </div>

      {error && email && (
        <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
          {error}
        </div>
      )}

      {saved && (
        <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded-lg text-sm text-green-700">
          {t("prefsSaved")}
        </div>
      )}

      <button
        onClick={handleSave}
        disabled={saving}
        className="mt-4 w-full bg-primary-600 text-white font-medium px-6 py-3 rounded-lg hover:bg-primary-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {saving ? t("savingPrefs") : t("savePrefs")}
      </button>

      <p className="text-center text-xs text-gray-500 mt-4">
        {t("stopAll")}{" "}
        <Link href={`/unsubscribe/${token}`} className="text-primary-600 hover:text-primary-700 underline">
          {t("unsubscribeAll")}
        </Link>
      </p>
    </div>
  );
}
