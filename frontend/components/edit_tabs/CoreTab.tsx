"use client";

/**
 * Core tab — identity + education statistics. Two sections:
 *   1. Identity (from MOE — read-only)
 *   2. Editable details (Tamil name + enrolment + sessions)
 */

import { useTranslations } from "next-intl";
import { SchoolEditData } from "@/lib/types";
import { ReadOnlyField, EditableField, SelectField } from "./FieldRow";

// MOE only publishes two SESI values. A free-text input let admins type
// "Pagi", "Morning", "AM", "pagi sahaja" etc., which broke the
// `session_${value}` i18n lookup and the public profile fallback prose.
// Sprint 26 bug #2 made this a constrained select.
const SESSION_TYPE_OPTIONS = [
  { value: "Pagi Sahaja", labelKey: "session_Pagi Sahaja" },
  { value: "Pagi dan Petang", labelKey: "session_Pagi dan Petang" },
];

interface CoreTabProps {
  data: SchoolEditData;
  onChange: (key: keyof SchoolEditData, value: string | number) => void;
}

export default function CoreTab({ data, onChange }: CoreTabProps) {
  const t = useTranslations("schoolEdit");

  return (
    <div className="space-y-8">
      <section>
        <p className="text-xs uppercase tracking-wider text-gray-500 font-semibold mb-3">
          {t("identityFromMoe")}
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <ReadOnlyField label={t("officialName")} value={data.name} />
          <ReadOnlyField label={t("shortName")} value={data.short_name} />
          <ReadOnlyField label={t("moeCode")} value={data.moe_code} />
          <ReadOnlyField label={t("state")} value={data.state} />
          <ReadOnlyField label={t("ppd")} value={data.ppd} />
          <ReadOnlyField
            label={t("grade")}
            value={data.grade}
            badge={
              data.grade ? (
                <span className="inline-flex items-center px-2 py-0.5 text-xs font-semibold bg-blue-100 text-blue-800 rounded">
                  {data.grade}
                </span>
              ) : null
            }
          />
          <ReadOnlyField label={t("assistanceType")} value={data.assistance_type} />
          <ReadOnlyField label={t("locationType")} value={data.location_type} />
          <ReadOnlyField label={t("skmEligible")} value={data.skm_eligible ? t("yes") : t("no")} />
        </div>
      </section>

      <section>
        <p className="text-xs uppercase tracking-wider text-blue-700 font-semibold mb-3">
          {t("editableDetails")}
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <EditableField
            label={t("nameTamil")}
            value={data.name_tamil}
            onChange={(v) => onChange("name_tamil", v)}
            fullWidth
          />
          <EditableField
            label={t("studentEnrolment")}
            value={data.enrolment}
            onChange={(v) => onChange("enrolment", v === "" ? 0 : Number(v))}
            type="number"
          />
          <EditableField
            label={t("teacherCount")}
            value={data.teacher_count}
            onChange={(v) => onChange("teacher_count", v === "" ? 0 : Number(v))}
            type="number"
          />
          <EditableField
            label={t("preschoolEnrolment")}
            value={data.preschool_enrolment}
            onChange={(v) => onChange("preschool_enrolment", v === "" ? 0 : Number(v))}
            type="number"
          />
          <EditableField
            label={t("specialEnrolment")}
            value={data.special_enrolment}
            onChange={(v) => onChange("special_enrolment", v === "" ? 0 : Number(v))}
            type="number"
          />
          <EditableField
            label={t("sessionsPerDay")}
            value={data.session_count}
            onChange={(v) => onChange("session_count", v === "" ? 0 : Number(v))}
            type="number"
          />
          <SelectField
            label={t("sessionType")}
            value={data.session_type ?? ""}
            options={SESSION_TYPE_OPTIONS.map((o) => ({
              value: o.value,
              label: t.has(o.labelKey) ? t(o.labelKey) : o.value,
            }))}
            onChange={(v) => onChange("session_type", v)}
          />
        </div>
      </section>
    </div>
  );
}
