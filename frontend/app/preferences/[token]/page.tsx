import { Metadata } from "next";
import PreferencesForm from "@/components/PreferencesForm";
import Breadcrumb from "@/components/Breadcrumb";

export const metadata: Metadata = {
  title: "Manage Preferences | SJK(T) Connect",
  description: "Manage your SJK(T) Connect subscription preferences.",
};

interface PreferencesPageProps {
  params: Promise<{ token: string }>;
}

export default async function PreferencesPage({ params }: PreferencesPageProps) {
  const { token } = await params;

  return (
    <main className="max-w-lg mx-auto px-4 py-8">
      <Breadcrumb
        items={[
          { label: "Home", href: "/" },
          { label: "Manage Preferences" },
        ]}
      />

      <div className="mt-6 bg-white rounded-lg shadow-sm border p-6">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">
          Subscription Preferences
        </h1>
        <p className="text-gray-600 mb-6">
          Choose which types of intelligence you&apos;d like to receive.
        </p>

        <PreferencesForm token={token} />
      </div>
    </main>
  );
}
