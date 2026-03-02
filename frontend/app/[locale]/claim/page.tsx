import { Metadata } from "next";
import ClaimForm from "@/components/ClaimForm";
import Breadcrumb from "@/components/Breadcrumb";

export const metadata: Metadata = {
  title: "Claim Your School | SJK(T) Connect",
  description:
    "Verify and update your Tamil school's information on SJK(T) Connect. Requires a valid @moe.edu.my email address.",
};

export default function ClaimPage() {
  return (
    <main className="max-w-lg mx-auto px-4 py-8">
      <Breadcrumb
        items={[
          { label: "Home", href: "/" },
          { label: "Claim Your School" },
        ]}
      />

      <div className="mt-6 bg-white rounded-lg shadow-sm border p-6">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">
          Claim Your School
        </h1>
        <p className="text-gray-600 mb-6">
          Enter your school&apos;s official MOE email address to verify your
          identity. We&apos;ll send you a link to confirm and manage your
          school&apos;s page.
        </p>

        <ClaimForm />
      </div>

      <div className="mt-6 bg-gray-50 rounded-lg p-4">
        <h2 className="text-sm font-semibold text-gray-700 mb-2">
          How it works
        </h2>
        <ol className="text-sm text-gray-600 space-y-2 list-decimal list-inside">
          <li>Enter your school&apos;s @moe.edu.my email address</li>
          <li>Check your inbox for the verification link</li>
          <li>Click the link to verify your identity</li>
          <li>You can then confirm or update your school&apos;s information</li>
        </ol>
      </div>
    </main>
  );
}
