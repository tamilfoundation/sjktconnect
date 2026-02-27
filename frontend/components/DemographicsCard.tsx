interface DemographicsCardProps {
  indianPopulation: number | null;
  indianPercentage: number | null;
  avgIncome?: number | null;
  povertyRate?: number | null;
  gini?: number | null;
  unemploymentRate?: number | null;
}

export default function DemographicsCard({
  indianPopulation,
  indianPercentage,
  avgIncome,
  povertyRate,
  gini,
  unemploymentRate,
}: DemographicsCardProps) {
  const hasAnyData =
    indianPopulation != null ||
    indianPercentage != null ||
    avgIncome != null ||
    povertyRate != null;

  if (!hasAnyData) {
    return null;
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <h2 className="text-lg font-semibold text-gray-800 mb-4">
        Demographics
      </h2>
      <dl className="grid grid-cols-2 gap-x-8 gap-y-3 text-sm">
        {indianPopulation != null && (
          <div>
            <dt className="text-gray-500">Indian Population</dt>
            <dd className="text-gray-800 font-medium mt-0.5">
              {indianPopulation.toLocaleString()}
            </dd>
          </div>
        )}
        {indianPercentage != null && (
          <div>
            <dt className="text-gray-500">Indian %</dt>
            <dd className="text-gray-800 font-medium mt-0.5">
              {indianPercentage.toFixed(1)}%
            </dd>
          </div>
        )}
        {avgIncome != null && (
          <div>
            <dt className="text-gray-500">Avg. Income</dt>
            <dd className="text-gray-800 font-medium mt-0.5">
              RM {avgIncome.toLocaleString()}
            </dd>
          </div>
        )}
        {povertyRate != null && (
          <div>
            <dt className="text-gray-500">Poverty Rate</dt>
            <dd className="text-gray-800 font-medium mt-0.5">
              {povertyRate.toFixed(1)}%
            </dd>
          </div>
        )}
        {gini != null && (
          <div>
            <dt className="text-gray-500">Gini Index</dt>
            <dd className="text-gray-800 font-medium mt-0.5">
              {gini.toFixed(3)}
            </dd>
          </div>
        )}
        {unemploymentRate != null && (
          <div>
            <dt className="text-gray-500">Unemployment</dt>
            <dd className="text-gray-800 font-medium mt-0.5">
              {unemploymentRate.toFixed(1)}%
            </dd>
          </div>
        )}
      </dl>
    </div>
  );
}
