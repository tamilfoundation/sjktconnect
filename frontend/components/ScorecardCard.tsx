import { Scorecard } from "@/lib/types";

interface ScorecardCardProps {
  scorecard: Scorecard | null;
  mpName: string;
}

export default function ScorecardCard({
  scorecard,
  mpName,
}: ScorecardCardProps) {
  if (!scorecard) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-800 mb-3">
          Parliament Watch Scorecard
        </h2>
        <p className="text-sm text-gray-500">
          No parliamentary activity recorded for {mpName} yet.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <h2 className="text-lg font-semibold text-gray-800 mb-4">
        Parliament Watch Scorecard
      </h2>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="text-center">
          <div className="text-2xl font-bold text-primary-700">
            {scorecard.total_mentions}
          </div>
          <div className="text-xs text-gray-500 mt-1">Total Mentions</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-primary-700">
            {scorecard.substantive_mentions}
          </div>
          <div className="text-xs text-gray-500 mt-1">Substantive</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-primary-700">
            {scorecard.questions_asked}
          </div>
          <div className="text-xs text-gray-500 mt-1">Questions Asked</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-primary-700">
            {scorecard.commitments_made}
          </div>
          <div className="text-xs text-gray-500 mt-1">Commitments</div>
        </div>
      </div>
      {scorecard.last_mention_date && (
        <p className="text-xs text-gray-400 mt-4 text-center">
          Last mention:{" "}
          {new Date(scorecard.last_mention_date).toLocaleDateString("en-GB", {
            day: "numeric",
            month: "long",
            year: "numeric",
          })}
        </p>
      )}
    </div>
  );
}
