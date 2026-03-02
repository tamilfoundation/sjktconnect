import { Metadata } from "next";
import SubscribeForm from "@/components/SubscribeForm";
import Breadcrumb from "@/components/Breadcrumb";

export const metadata: Metadata = {
  title: "Subscribe | SJK(T) Connect",
  description:
    "Subscribe to SJK(T) Connect Intelligence Blast — parliamentary analysis, news monitoring, and monthly digests about Malaysia's 528 Tamil schools.",
};

export default function SubscribePage() {
  return (
    <main className="max-w-lg mx-auto px-4 py-8">
      <Breadcrumb
        items={[
          { label: "Home", href: "/" },
          { label: "Subscribe" },
        ]}
      />

      <div className="mt-6 bg-white rounded-lg shadow-sm border p-6">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">
          Subscribe to Intelligence Blast
        </h1>
        <p className="text-gray-600 mb-6">
          Stay informed about Malaysia&apos;s 528 Tamil schools. Receive
          parliamentary analysis, news alerts, and monthly intelligence digests.
        </p>

        <SubscribeForm />
      </div>

      <div className="mt-6 bg-gray-50 rounded-lg p-4">
        <h2 className="text-sm font-semibold text-gray-700 mb-2">
          What you&apos;ll receive
        </h2>
        <ul className="text-sm text-gray-600 space-y-2">
          <li className="flex items-start gap-2">
            <span className="font-medium text-primary-600">Parliament Watch</span>
            &mdash; when MPs discuss Tamil schools in Parliament
          </li>
          <li className="flex items-start gap-2">
            <span className="font-medium text-primary-600">News Watch</span>
            &mdash; media coverage affecting Tamil schools
          </li>
          <li className="flex items-start gap-2">
            <span className="font-medium text-primary-600">Monthly Blast</span>
            &mdash; comprehensive monthly intelligence digest
          </li>
        </ul>
      </div>
    </main>
  );
}
