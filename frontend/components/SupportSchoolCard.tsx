"use client";

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
  moeCode,
}: Props) {
  const t = useTranslations("schoolProfile");
  const [copied, setCopied] = useState(false);

  if (!bankAccountNumber) return null;

  const handleCopy = () => {
    navigator.clipboard.writeText(bankAccountNumber);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const apiBase = process.env.NEXT_PUBLIC_API_URL || "";
  const qrUrl = `${apiBase}/api/v1/schools/${moeCode}/duitnow-qr/`;

  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      <div className="h-1 bg-green-500" />
      <div className="p-4">
        <h3 className="font-semibold text-gray-900 mb-3">
          {t("supportSchool")}
        </h3>

        <div className="space-y-2 text-sm">
          <div>
            <span className="text-gray-500">{t("bankName")}</span>
            <p className="font-medium">{bankName}</p>
          </div>
          <div>
            <span className="text-gray-500">{t("accountName")}</span>
            <p className="font-medium text-xs">{bankAccountName}</p>
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

        {/* DuitNow QR */}
        <div className="mt-4 text-center">
          <p className="text-xs text-gray-500 mb-2">{t("scanToDonate")}</p>
          <img
            src={qrUrl}
            alt="DuitNow QR Code"
            className="mx-auto w-40 h-40 border rounded"
          />
        </div>
      </div>
    </div>
  );
}
