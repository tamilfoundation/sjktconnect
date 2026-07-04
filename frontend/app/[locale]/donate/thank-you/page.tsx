"use client";

import { useTranslations } from "next-intl";
import { useSearchParams } from "next/navigation";
import { Link } from "@/i18n/navigation";
import { Suspense, useEffect, useState } from "react";

interface DonationStatus {
  status: "paid" | "processing" | "failed";
  amount?: number;
  donor_name?: string;
  order_id?: string;
  donation_id?: string;
}

function ThankYouContent() {
  const t = useTranslations("donate");
  const searchParams = useSearchParams();
  // Audit 2026-07-01: return-URL now uses `donation_id` (UUID) instead
  // of the enumerable `order_id`. Fall back to legacy `order_id` for any
  // Toyyib bill still in-flight from before the switchover.
  const donationId = searchParams.get("donation_id") || "";
  const legacyOrderId = searchParams.get("order_id") || "";

  const [donation, setDonation] = useState<DonationStatus | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!donationId && !legacyOrderId) {
      setLoading(false);
      return;
    }

    const apiBase = process.env.NEXT_PUBLIC_API_URL || "";
    // New URL takes the UUID as a path segment. Legacy order_id was
    // never wired to a working URL (the old FE built a nonsense path),
    // so no fallback fetch — surfaces as "processing" via .catch below.
    const url = donationId
      ? `${apiBase}/api/v1/donations/status/${donationId}/`
      : "";

    if (!url) {
      setDonation({ status: "processing", order_id: legacyOrderId });
      setLoading(false);
      return;
    }

    fetch(url)
      .then((res) => {
        if (!res.ok) throw new Error("Failed to fetch");
        return res.json();
      })
      .then((data) => {
        setDonation(data);
        setLoading(false);
      })
      .catch(() => {
        setDonation({ status: "processing", donation_id: donationId });
        setLoading(false);
      });
  }, [donationId, legacyOrderId]);

  if (loading) {
    return (
      <div className="max-w-lg mx-auto px-4 py-16 text-center">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-48 mx-auto mb-4" />
          <div className="h-4 bg-gray-200 rounded w-64 mx-auto" />
        </div>
      </div>
    );
  }

  const isPaid = donation?.status === "paid";

  return (
    <div className="max-w-lg mx-auto px-4 py-16 text-center">
      {/* Icon */}
      <div className={`mx-auto w-16 h-16 rounded-full flex items-center justify-center mb-6 ${
        isPaid ? "bg-green-100" : "bg-amber-100"
      }`}>
        {isPaid ? (
          <svg className="w-8 h-8 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        ) : (
          <svg className="w-8 h-8 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        )}
      </div>

      {/* Heading */}
      <h1 className="text-3xl font-bold text-gray-900 mb-2">
        {isPaid ? t("thankYou") : t("paymentProcessing")}
      </h1>

      {/* Details */}
      {donation && (
        <div className="mt-6 space-y-2 text-gray-600">
          {isPaid && donation.amount && (
            <p className="text-2xl font-semibold text-gray-900">
              RM {donation.amount}
              {donation.donor_name && (
                <span className="text-base font-normal text-gray-500">
                  {" "}{t("receivedFrom")} {donation.donor_name}
                </span>
              )}
            </p>
          )}
          {(donation.order_id || legacyOrderId) && (
            <p className="text-sm text-gray-500">
              {t("referenceId")}: {donation.order_id || legacyOrderId}
            </p>
          )}
        </div>
      )}

      {/* Back to home */}
      <div className="mt-8">
        <Link
          href="/"
          className="inline-block px-6 py-3 text-sm font-medium bg-primary-600 text-white rounded-md hover:bg-primary-700 transition-colors"
        >
          {t("backToHome")}
        </Link>
      </div>
    </div>
  );
}

export default function ThankYouPage() {
  return (
    <Suspense
      fallback={
        <div className="max-w-lg mx-auto px-4 py-16 text-center">
          <div className="animate-pulse">
            <div className="h-8 bg-gray-200 rounded w-48 mx-auto mb-4" />
            <div className="h-4 bg-gray-200 rounded w-64 mx-auto" />
          </div>
        </div>
      }
    >
      <ThankYouContent />
    </Suspense>
  );
}
