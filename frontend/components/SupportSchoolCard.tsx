"use client";

/**
 * The DuitNow QR section was removed 2026-06-28 after owner-tested with
 * Maybank app and got "Invalid QR Code [MB02]". The endpoint had been
 * encoding plain text ("Bank: X\nAccount: Y\nName: Z"), not an EMVCo
 * DuitNow payload — a real DuitNow QR needs a PayNet-issued merchant ID
 * registered via each school's own bank, which we can't generate
 * unilaterally. Replaced with an explicit DuitNow Transfer instruction
 * so users can punch the account number into their banking app (which
 * actually works for any Malaysian account).
 */

import { useTranslations } from "next-intl";
import { useState } from "react";

interface Props {
  bankName: string;
  bankAccountNumber: string;
  bankAccountName: string;
  moeCode: string;
}

export default function SupportSchoolCard({
  bankName,
  bankAccountNumber,
  bankAccountName,
}: Props) {
  const t = useTranslations("schoolProfile");
  const [copied, setCopied] = useState(false);

  if (!bankAccountNumber) return null;

  const handleCopy = () => {
    navigator.clipboard.writeText(bankAccountNumber);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      <div className="h-1 bg-green-500" />
      <div className="p-4">
        <h3 className="font-semibold text-gray-900 mb-3">
          {t("supportSchool")}
        </h3>

        <div className="space-y-3 text-sm">
          {/* Audit 2026-07-01: stack Bank / Account Number vertically at
              <sm so a long bank name doesn't push the account number
              off-screen at 375 px. */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <span className="text-gray-500">{t("bankName")}</span>
              <p className="font-medium">{bankName}</p>
            </div>
            <div>
              <span className="text-gray-500">{t("accountNumber")}</span>
              <div className="flex items-center gap-2">
                <p className="font-mono font-medium">{bankAccountNumber}</p>
                <button
                  onClick={handleCopy}
                  className="text-xs text-primary-600 hover:text-primary-800"
                >
                  {copied ? t("copied") : t("copy")}
                </button>
              </div>
            </div>
          </div>
          <div>
            <span className="text-gray-500">{t("accountName")}</span>
            <p className="font-medium text-xs">{bankAccountName}</p>
          </div>
        </div>

      </div>
    </div>
  );
}
