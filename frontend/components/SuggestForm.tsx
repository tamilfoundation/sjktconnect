"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { createSuggestion } from "@/lib/api";

const SUGGESTIBLE_FIELDS = [
  "phone",
  "fax",
  "address",
  "postcode",
  "city",
  "gps_lat",
  "gps_lng",
  "grade",
  "assistance_type",
  "bank_name",
  "bank_account_number",
  "bank_account_name",
] as const;

const FIELD_LABELS: Record<string, string> = {
  phone: "Phone",
  fax: "Fax",
  address: "Address",
  postcode: "Postcode",
  city: "City",
  gps_lat: "GPS Latitude",
  gps_lng: "GPS Longitude",
  grade: "Grade",
  assistance_type: "Assistance Type",
  bank_name: "Bank Name",
  bank_account_number: "Bank Account Number",
  bank_account_name: "Bank Account Name",
};

interface SuggestFormProps {
  moeCode: string;
  onClose: () => void;
}

export default function SuggestForm({ moeCode, onClose }: SuggestFormProps) {
  const t = useTranslations("suggestions");

  const [type, setType] = useState<"DATA_CORRECTION" | "PHOTO_UPLOAD" | "NOTE">(
    "DATA_CORRECTION"
  );
  const [fieldName, setFieldName] = useState("");
  const [suggestedValue, setSuggestedValue] = useState("");
  const [note, setNote] = useState("");
  const [imageBase64, setImageBase64] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState("");

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result as string;
      setImageBase64(result);
    };
    reader.readAsDataURL(file);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError("");

    try {
      const data: {
        type: string;
        field_name?: string;
        suggested_value?: string;
        note?: string;
        image?: string;
      } = { type };

      if (type === "DATA_CORRECTION") {
        data.field_name = fieldName;
        data.suggested_value = suggestedValue;
      } else if (type === "NOTE") {
        data.note = note;
      } else if (type === "PHOTO_UPLOAD") {
        data.image = imageBase64;
      }

      await createSuggestion(moeCode, data);
      setSuccess(true);
    } catch {
      setError(t("error"));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="bg-white rounded-xl shadow-xl max-w-lg w-full max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <h2 className="text-lg font-semibold text-gray-900">
            {t("suggestEdit")}
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {success ? (
          <div className="p-6 text-center">
            <div className="w-12 h-12 rounded-full bg-green-100 flex items-center justify-center mx-auto mb-3">
              <svg className="w-6 h-6 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <p className="text-green-700 font-medium mb-4">{t("success")}</p>
            <button
              onClick={onClose}
              className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors text-sm"
            >
              {t("cancel")}
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="p-6 space-y-5">
            {/* Type selector */}
            <fieldset className="space-y-2">
              <div className="flex flex-col gap-2">
                {(
                  [
                    ["DATA_CORRECTION", t("dataCorrection")],
                    ["PHOTO_UPLOAD", t("photoUpload")],
                    ["NOTE", t("note")],
                  ] as const
                ).map(([value, label]) => (
                  <label
                    key={value}
                    className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                      type === value
                        ? "border-primary-500 bg-primary-50"
                        : "border-gray-200 hover:bg-gray-50"
                    }`}
                  >
                    <input
                      type="radio"
                      name="type"
                      value={value}
                      checked={type === value}
                      onChange={() => setType(value)}
                      className="text-primary-600"
                    />
                    <span className="text-sm font-medium text-gray-700">
                      {label}
                    </span>
                  </label>
                ))}
              </div>
            </fieldset>

            {/* DATA_CORRECTION fields */}
            {type === "DATA_CORRECTION" && (
              <div className="space-y-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    {t("selectField")}
                  </label>
                  <select
                    value={fieldName}
                    onChange={(e) => setFieldName(e.target.value)}
                    required
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                  >
                    <option value="">{t("selectField")}</option>
                    {SUGGESTIBLE_FIELDS.map((f) => (
                      <option key={f} value={f}>
                        {FIELD_LABELS[f]}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    {t("newValue")}
                  </label>
                  <input
                    type="text"
                    value={suggestedValue}
                    onChange={(e) => setSuggestedValue(e.target.value)}
                    required
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                  />
                </div>
              </div>
            )}

            {/* NOTE field */}
            {type === "NOTE" && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {t("yourNote")}
                </label>
                <textarea
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  required
                  rows={4}
                  placeholder={t("yourNote")}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                />
              </div>
            )}

            {/* PHOTO_UPLOAD field */}
            {type === "PHOTO_UPLOAD" && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {t("uploadPhoto")}
                </label>
                <input
                  type="file"
                  accept="image/*"
                  onChange={handleFileChange}
                  required
                  className="w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-primary-50 file:text-primary-700 hover:file:bg-primary-100"
                />
                {imageBase64 && (
                  <div className="mt-2">
                    <img
                      src={imageBase64}
                      alt="Preview"
                      className="w-full max-h-48 object-cover rounded-lg"
                    />
                  </div>
                )}
              </div>
            )}

            {error && (
              <p className="text-sm text-red-600 bg-red-50 rounded-lg p-3">
                {error}
              </p>
            )}

            {/* Actions */}
            <div className="flex gap-3 justify-end pt-2">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
              >
                {t("cancel")}
              </button>
              <button
                type="submit"
                disabled={submitting}
                className="px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-700 disabled:opacity-50 transition-colors"
              >
                {submitting ? t("submitting") : t("submit")}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
