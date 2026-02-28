import { Metadata } from "next";

export const metadata: Metadata = {
  title: "Parliament Watch — SJK(T) Connect",
  description:
    "Tracking how Malaysian MPs discuss Tamil schools in Parliament. AI-powered Hansard analysis and MP scorecards.",
};

export default function ParliamentWatchPage() {
  return (
    <div className="max-w-4xl mx-auto px-4 py-12">
      <h1 className="text-3xl font-bold text-gray-900 mb-4">
        Parliament Watch
      </h1>
      <p className="text-lg text-gray-600 mb-8">
        Tracking how Malaysian MPs discuss Tamil schools in Parliament.
        AI-powered analysis of Hansard proceedings with MP scorecards.
      </p>

      <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
        <h2 className="text-lg font-semibold text-blue-900 mb-2">
          Coming Soon
        </h2>
        <p className="text-blue-800">
          Parliament Watch reports are currently available on the admin portal.
          Public access will be enabled in a future update. In the meantime,
          explore the{" "}
          <a href="/" className="underline font-medium">
            school map
          </a>{" "}
          and{" "}
          <a href="/constituencies" className="underline font-medium">
            constituency pages
          </a>
          .
        </p>
      </div>
    </div>
  );
}
