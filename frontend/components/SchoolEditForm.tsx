"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { SchoolEditData } from "@/lib/types";
import { updateSchool, confirmSchool } from "@/lib/api";

interface SchoolEditFormProps {
  school: SchoolEditData;
}

interface FieldConfig {
  key: keyof SchoolEditData;
  labelKey: string;
  type: "text" | "number" | "email" | "tel";
  readOnly?: boolean;
}

const FIELDS: FieldConfig[] = [
  { key: "name", labelKey: "officialName", type: "text", readOnly: true },
  { key: "short_name", labelKey: "shortName", type: "text", readOnly: true },
  { key: "state", labelKey: "state", type: "text", readOnly: true },
  { key: "name_tamil", labelKey: "nameTamil", type: "text" },
  { key: "address", labelKey: "address", type: "text" },
  { key: "postcode", labelKey: "postcode", type: "text" },
  { key: "city", labelKey: "city", type: "text" },
  { key: "email", labelKey: "email", type: "email" },
  { key: "phone", labelKey: "phone", type: "tel" },
  { key: "fax", labelKey: "fax", type: "tel" },
  { key: "enrolment", labelKey: "studentEnrolment", type: "number" },
  { key: "preschool_enrolment", labelKey: "preschoolEnrolment", type: "number" },
  { key: "special_enrolment", labelKey: "specialEnrolment", type: "number" },
  { key: "teacher_count", labelKey: "teacherCount", type: "number" },
  { key: "session_count", labelKey: "sessionsPerDay", type: "number" },
  { key: "session_type", labelKey: "sessionType", type: "text" },
];

export default function SchoolEditForm({ school }: SchoolEditFormProps) {
  const t = useTranslations("schoolEdit");
  const tc = useTranslations("common");
  const [formData, setFormData] = useState<SchoolEditData>(school);
  const [saving, setSaving] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [success, setSuccess] = useState("");
  const [error, setError] = useState("");

  function handleChange(key: keyof SchoolEditData, value: string) {
    setFormData((prev) => ({
      ...prev,
      [key]: FIELDS.find((f) => f.key === key)?.type === "number"
        ? value === "" ? 0 : Number(value)
        : value,
    }));
  }

  async function handleConfirm() {
    setConfirming(true);
    setError("");
    setSuccess("");
    try {
      const result = await confirmSchool(school.moe_code);
      setSuccess(`Data confirmed at ${new Date(result.last_verified).toLocaleString()}`);
      setFormData((prev) => ({
        ...prev,
        last_verified: result.last_verified,
        verified_by: result.verified_by,
      }));
    } catch (err) {
      setError(err instanceof Error ? err.message : t("failedConfirm"));
    } finally {
      setConfirming(false);
    }
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError("");
    setSuccess("");

    // Only send changed (writable) fields
    const updates: Record<string, unknown> = {};
    for (const field of FIELDS) {
      if (field.readOnly) continue;
      if (formData[field.key] !== school[field.key]) {
        updates[field.key] = formData[field.key];
      }
    }

    if (Object.keys(updates).length === 0) {
      setError(t("noChanges"));
      setSaving(false);
      return;
    }

    try {
      const result = await updateSchool(school.moe_code, updates);
      setSuccess(t("changesSaved"));
      setFormData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("failedSave"));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div>
      {/* Confirm Button — prominent, above form */}
      <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold text-green-800">
              {t("isCorrect")}
            </h3>
            <p className="text-sm text-green-700 mt-1">
              {t("confirmOrEdit")}
            </p>
          </div>
          <button
            type="button"
            onClick={handleConfirm}
            disabled={confirming}
            className="px-6 py-2 bg-green-600 text-white text-sm font-medium rounded-lg hover:bg-green-700 disabled:opacity-50 whitespace-nowrap"
          >
            {confirming ? t("confirming") : t("confirmData")}
          </button>
        </div>
        {formData.last_verified && (
          <p className="text-xs text-green-600 mt-2">
            {t("lastVerified")} {new Date(formData.last_verified).toLocaleString()}
            {formData.verified_by && ` ${t("by")} ${formData.verified_by}`}
          </p>
        )}
      </div>

      {/* Status messages */}
      {success && (
        <div className="bg-green-50 border border-green-200 text-green-800 rounded-lg p-3 mb-4 text-sm">
          {success}
        </div>
      )}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-800 rounded-lg p-3 mb-4 text-sm">
          {error}
        </div>
      )}

      {/* Edit Form */}
      <form onSubmit={handleSave}>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {FIELDS.map((field) => (
            <div key={field.key}>
              <label
                htmlFor={`field-${field.key}`}
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                {t(field.labelKey)}
                {field.readOnly && (
                  <span className="text-gray-400 ml-1">{t("readOnly")}</span>
                )}
              </label>
              <input
                id={`field-${field.key}`}
                type={field.type}
                value={formData[field.key] ?? ""}
                onChange={(e) => handleChange(field.key, e.target.value)}
                readOnly={field.readOnly}
                className={`w-full px-3 py-2 border rounded-lg text-sm ${
                  field.readOnly
                    ? "bg-gray-50 text-gray-500 border-gray-200"
                    : "bg-white text-gray-900 border-gray-300 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                }`}
              />
            </div>
          ))}
        </div>

        <div className="mt-6 flex gap-3">
          <button
            type="submit"
            disabled={saving}
            className="px-6 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {saving ? t("saving") : t("saveChanges")}
          </button>
          <Link
            href={`/school/${school.moe_code}`}
            className="px-6 py-2 bg-gray-100 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-200"
          >
            {tc("cancel")}
          </Link>
        </div>
      </form>
    </div>
  );
}
