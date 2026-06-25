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
  /**
   * Inline validation message. Empty string = field is valid. When non-
   * empty: red border, red text, browser-level invalid styling. Sprint
   * 26 bug #1 added this — previously phone/email took any string.
   */
  error?: string;
  /**
   * HTML5 `pattern` attribute. Combined with browser native validation
   * to refuse submit on invalid values; the `error` prop also surfaces
   * the message inline so users don't have to dismiss a tooltip.
   */
  pattern?: string;
  /** Hint shown to native validation tooltip when pattern fails. */
  patternTitle?: string;
}

export function EditableField({
  label,
  value,
  onChange,
  type = "text",
  placeholder,
  id,
  fullWidth = false,
  error,
  pattern,
  patternTitle,
}: EditableFieldProps) {
  const inputId = id ?? `field-${label.toLowerCase().replace(/\s+/g, "-")}`;
  const hasError = Boolean(error);
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
        pattern={pattern}
        title={patternTitle}
        aria-invalid={hasError || undefined}
        aria-describedby={hasError ? `${inputId}-error` : undefined}
        onChange={(e) => onChange(e.target.value)}
        className={`w-full px-3 py-2 bg-white border rounded-lg text-sm focus:ring-2 ${
          hasError
            ? "border-red-400 focus:ring-red-500 focus:border-red-500"
            : "border-gray-300 focus:ring-blue-500 focus:border-blue-500"
        }`}
      />
      {hasError && (
        <p
          id={`${inputId}-error`}
          className="mt-1 text-xs text-red-600"
        >
          {error}
        </p>
      )}
    </div>
  );
}

interface SelectFieldProps {
  label: string;
  value: string;
  options: { value: string; label: string }[];
  onChange: (value: string) => void;
  id?: string;
  fullWidth?: boolean;
  /** Render a blank "choose…" option as the first item. */
  allowEmpty?: boolean;
  emptyLabel?: string;
}

/**
 * Constrained variant of EditableField — a `<select>` populated from a
 * known enum (e.g. Session Type, which MOE only ever publishes as
 * `Pagi Sahaja` or `Pagi dan Petang`). Sprint 26 bug #2 replaced the
 * free-text input that let admins type arbitrary garbage.
 */
export function SelectField({
  label,
  value,
  options,
  onChange,
  id,
  fullWidth = false,
  allowEmpty = true,
  emptyLabel = "—",
}: SelectFieldProps) {
  const inputId = id ?? `field-${label.toLowerCase().replace(/\s+/g, "-")}`;
  return (
    <div className={fullWidth ? "md:col-span-2" : ""}>
      <label htmlFor={inputId} className="block text-sm font-medium text-gray-800 mb-1">
        {label}
      </label>
      <select
        id={inputId}
        value={value ?? ""}
        onChange={(e) => onChange(e.target.value)}
        className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
      >
        {allowEmpty && <option value="">{emptyLabel}</option>}
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>{opt.label}</option>
        ))}
      </select>
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
