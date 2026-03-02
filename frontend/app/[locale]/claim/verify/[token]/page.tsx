"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { verifyMagicLink } from "@/lib/api";
import { AuthUser } from "@/lib/types";

export default function VerifyPage() {
  const params = useParams();
  const token = params.token as string;
  const [user, setUser] = useState<AuthUser | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function verify() {
      try {
        const result = await verifyMagicLink(token);
        setUser(result);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Verification failed."
        );
      } finally {
        setLoading(false);
      }
    }
    verify();
  }, [token]);

  if (loading) {
    return (
      <main className="max-w-lg mx-auto px-4 py-16 text-center">
        <div className="animate-pulse">
          <div className="h-16 w-16 bg-gray-200 rounded-full mx-auto mb-4" />
          <div className="h-6 bg-gray-200 rounded w-48 mx-auto mb-2" />
          <div className="h-4 bg-gray-200 rounded w-64 mx-auto" />
        </div>
        <p className="text-gray-500 mt-4">Verifying your email...</p>
      </main>
    );
  }

  if (error) {
    return (
      <main className="max-w-lg mx-auto px-4 py-16 text-center">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-red-100 mb-4">
          <svg className="w-8 h-8 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </div>
        <h1 className="text-xl font-semibold text-gray-900 mb-2">
          Verification Failed
        </h1>
        <p className="text-gray-600 mb-6">{error}</p>
        <Link
          href="/claim/"
          className="inline-block bg-primary-600 text-white font-medium px-6 py-3 rounded-lg hover:bg-primary-700 transition-colors"
        >
          Try Again
        </Link>
      </main>
    );
  }

  return (
    <main className="max-w-lg mx-auto px-4 py-16 text-center">
      <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-green-100 mb-4">
        <svg className="w-8 h-8 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
        </svg>
      </div>
      <h1 className="text-xl font-semibold text-gray-900 mb-2">
        Email Verified!
      </h1>
      <p className="text-gray-600 mb-2">
        You are now linked to <strong>{user?.school_name}</strong>.
      </p>
      <p className="text-sm text-gray-500 mb-6">
        Signed in as {user?.email}
      </p>
      <Link
        href={`/school/${user?.school_moe_code}`}
        className="inline-block bg-primary-600 text-white font-medium px-6 py-3 rounded-lg hover:bg-primary-700 transition-colors"
      >
        Go to Your School Page
      </Link>
    </main>
  );
}
