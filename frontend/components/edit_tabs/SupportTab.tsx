"use client";

/**
 * Support tab — bank details that power the SupportSchoolCard +
 * DuitNow QR on the public school page.
 */

import { useTranslations } from "next-intl";
import { SchoolEditData } from "@/lib/types";
import { EditableField } from "./FieldRow";

interface SupportTabProps {
  data: SchoolEditData;
  onChange: (key: keyof SchoolEditData, value: string | number) => void;
}

export default function SupportTab({ data, onChange }: SupportTabProps) {
  const t = useTranslations("schoolEdit");

  return (
    <div className="space-y-6">
      <p className="text-sm text-gray-600">{t("supportIntro")}</p>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <EditableField
          label={t("bankName")}
          value={data.bank_name}
          onChange={(v) => onChange("bank_name", v)}
          fullWidth
        />
        <EditableField
          label={t("bankAccountName")}
          value={data.bank_account_name}
          onChange={(v) => onChange("bank_account_name", v)}
          fullWidth
        />
        <EditableField
          label={t("bankAccountNumber")}
          value={data.bank_account_number}
          onChange={(v) => onChange("bank_account_number", v)}
          fullWidth
        />
      </div>
    </div>
  );
}
