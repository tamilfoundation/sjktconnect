"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";

const PRESET_AMOUNTS = [10, 50, 100, 250];

export default function DonationForm() {
  const t = useTranslations("donate");
  const [amount, setAmount] = useState<number | "">("");
  const [customAmount, setCustomAmount] = useState("");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const selectedAmount = typeof amount === "number" ? amount : Number(customAmount) || 0;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (selectedAmount < 1 || !name || !email) return;

    setLoading(true);
    setError("");

    try {
      const apiBase = process.env.NEXT_PUBLIC_API_URL || "";
      const res = await fetch(`${apiBase}/api/v1/donations/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          amount: selectedAmount,
          donor_name: name,
          donor_email: email,
          donor_phone: phone,
          message,
        }),
      });

      if (!res.ok) throw new Error("Payment service unavailable");

      const data = await res.json();
      window.location.href = data.payment_url;
    } catch (err) {
      setError(t("paymentError"));
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Amount selection */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          {t("selectAmount")}
        </label>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {PRESET_AMOUNTS.map((a) => (
            <button
              key={a}
              type="button"
              onClick={() => { setAmount(a); setCustomAmount(""); }}
              className={`py-3 px-4 rounded-lg border text-center font-semibold transition ${
                amount === a
                  ? "border-primary-600 bg-primary-50 text-primary-700"
                  : "border-gray-300 hover:border-gray-400"
              }`}
            >
              RM {a}
            </button>
          ))}
        </div>
        <div className="mt-3">
          <input
            type="number"
            min="1"
            placeholder={t("customAmount")}
            value={customAmount}
            onChange={(e) => { setCustomAmount(e.target.value); setAmount(""); }}
            className="w-full border border-gray-300 rounded-lg px-4 py-3 focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
          />
        </div>
      </div>

      {/* Donor info */}
      <div className="space-y-4">
        <input
          type="text"
          required
          placeholder={t("yourName")}
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="w-full border border-gray-300 rounded-lg px-4 py-3"
        />
        <input
          type="email"
          required
          placeholder={t("yourEmail")}
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="w-full border border-gray-300 rounded-lg px-4 py-3"
        />
        <input
          type="tel"
          placeholder={t("yourPhone")}
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
          className="w-full border border-gray-300 rounded-lg px-4 py-3"
        />
        <textarea
          placeholder={t("optionalMessage")}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          rows={3}
          className="w-full border border-gray-300 rounded-lg px-4 py-3"
        />
      </div>

      {error && <p className="text-red-600 text-sm">{error}</p>}

      <button
        type="submit"
        disabled={loading || selectedAmount < 1 || !name || !email}
        className="w-full bg-primary-600 text-white py-3 px-6 rounded-lg font-semibold hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
      >
        {loading ? t("processing") : `${t("donate")} RM ${selectedAmount || "..."}`}
      </button>
    </form>
  );
}
