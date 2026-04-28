"use client";

/**
 * Two visual variants of a labelled field used across all edit tabs.
 *
 *   <ReadOnlyField label="MOE Code" value="KBD6019" />
 *   <EditableField label="Name (Tamil)" value={name} onChange={setName} />
 *
 * Read-only fields show a small lock icon and a muted background so the
 * "MOE source — not editable here" semantics are visible without a
 * paragraph of help text.
 */

import { ReactNode } from "react";

interface ReadOnlyFieldProps {
  label: string;
  value: string | number | boolean | null | undefined;
  /** Optional badge/chip rendered to the right of the value (e.g. for Grade). */
  badge?: ReactNode;
}

export function ReadOnlyField({ label, value, badge }: ReadOnlyFieldProps) {
  const displayValue = formatValue(value);
  return (
    <div>
      <label className="flex items-center gap-1.5 text-xs font-medium text-gray-500 mb-1">
        <LockIcon />
        {label}
      </label>
      <div className="flex items-center gap-2 px-3 py-2 bg-gray-50 text-gray-700 text-sm rounded-lg border border-gray-200">
        <span className="flex-1 truncate">{displayValue || "—"}</span>
        {badge}
      </div>
    </div>
  );
}

interface EditableFieldProps {
  label: string;
  value: string | number;
  onChange: (value: string) => void;
  type?: "text" | "number" | "email" | "tel";
  placeholder?: string;
  id?: string;
  /** Render as a full-width row spanning both columns of the parent grid. */
  fullWidth?: boolean;
}

export function EditableField({
  label,
  value,
  onChange,
  type = "text",
  placeholder,
  id,
  fullWidth = false,
}: EditableFieldProps) {
  const inputId = id ?? `field-${label.toLowerCase().replace(/\s+/g, "-")}`;
  return (
    <div className={fullWidth ? "md:col-span-2" : ""}>
      <label htmlFor={inputId} className="block text-sm font-medium text-gray-800 mb-1">
        {label}
      </label>
      <input
        id={inputId}
        type={type}
        value={value ?? ""}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
      />
    </div>
  );
}

function formatValue(value: string | number | boolean | null | undefined): string {
  if (value === null || value === undefined) return "";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  return String(value);
}

function LockIcon() {
  return (
    <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M12 11c0-1.657 1.343-3 3-3s3 1.343 3 3v1H6v-1c0-3.314 2.686-6 6-6s6 2.686 6 6v1M6 12h12v8H6v-8z"
      />
    </svg>
  );
}
