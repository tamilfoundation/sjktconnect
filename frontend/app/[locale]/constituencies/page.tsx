import { Metadata } from "next";
import { fetchConstituencies } from "@/lib/api";
import ConstituencyList from "@/components/ConstituencyList";

export const revalidate = 3600;

export const metadata: Metadata = {
  title: "Constituencies — SJK(T) Connect",
  description:
    "Browse all 222 parliamentary constituencies with Tamil schools in Malaysia. See MP details, school counts, and scorecards.",
  openGraph: {
    title: "Constituencies — SJK(T) Connect",
    description:
      "Browse all parliamentary constituencies with Tamil schools in Malaysia.",
    type: "website",
    siteName: "SJK(T) Connect",
  },
};

export default async function ConstituenciesPage() {
  const constituencies = await fetchConstituencies();

  // Extract unique states
  const states = Array.from(
    new Set(constituencies.map((c) => c.state))
  ).sort();

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      <div className="mb-6">
        <h1 className="text-2xl sm:text-3xl font-bold text-gray-900">
          Constituencies
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          {constituencies.length} parliamentary constituencies with Tamil
          schools
        </p>
      </div>

      <ConstituencyList
        constituencies={constituencies}
        states={states}
      />
    </div>
  );
}
