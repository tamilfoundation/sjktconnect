"use client";

import { useTranslations } from "next-intl";
import { ElectoralInfluence } from "@/lib/types";

interface ElectoralInfluenceCardProps {
  influence: ElectoralInfluence | null;
  constituencyName?: string;
  constituencyCode?: string;
  state?: string;
}

function PowerMeter({ ratio, verdict }: { ratio: number; verdict: string }) {
  // Map ratio to fill percentage: 0x=5%, 1x=20%, 5x=60%, 10x=80%, 20x+=95%
  const fillPct = Math.max(5, Math.min(95, ratio > 5 ? 60 + ((ratio - 5) / 25) * 35 : (ratio / 5) * 55 + 5));

  const meterStyles: Record<string, { fill: string; track: string; label: string; pct: string }> = {
    kingmaker: {
      fill: "bg-gradient-to-t from-red-600 via-orange-500 to-yellow-400",
      track: "bg-red-100",
      label: "text-red-500",
      pct: "text-red-600",
    },
    significant: {
      fill: "bg-gradient-to-t from-amber-500 to-yellow-300",
      track: "bg-amber-100",
      label: "text-amber-500",
      pct: "text-amber-600",
    },
    safe_seat: {
      fill: "bg-slate-400",
      track: "bg-slate-200",
      label: "text-slate-400",
      pct: "text-slate-500",
    },
  };

  const styles = meterStyles[verdict] || meterStyles.safe_seat;

  return (
    <div className="flex flex-col items-center py-5">
      {/* Vertical capsule power meter */}
      <div className={`relative w-12 h-24 rounded-full ${styles.track} overflow-hidden shadow-inner`}>
        <div
          className={`absolute bottom-0 left-0 right-0 ${styles.fill} transition-all duration-700 ease-out`}
          style={{ height: `${fillPct}%` }}
        />
      </div>
      <div className={`text-[10px] font-semibold ${styles.label} uppercase tracking-wider mt-2`}>
        Power Meter
      </div>
      <div className={`text-lg font-bold ${styles.pct}`}>
        {Math.round(fillPct)}%
      </div>
    </div>
  );
}

export default function ElectoralInfluenceCard({
  influence,
  constituencyName,
  constituencyCode,
  state,
}: ElectoralInfluenceCardProps) {
  const t = useTranslations("constituency");

  if (!influence) return null;

  const isKingmaker = influence.verdict === "kingmaker";
  const isSafeSeat = influence.verdict === "safe_seat";

  const verdictConfig: Record<
    string,
    { bg: string; text: string; icon: string }
  > = {
    kingmaker: {
      bg: "bg-red-600 hover:bg-red-700",
      text: "text-white",
      icon: "M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z",
    },
    significant: {
      bg: "bg-amber-500 hover:bg-amber-600",
      text: "text-white",
      icon: "M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z",
    },
    safe_seat: {
      bg: "bg-slate-100",
      text: "text-slate-500",
      icon: "M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z",
    },
  };

  const config = verdictConfig[influence.verdict] || verdictConfig.safe_seat;

  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      {/* Power gauge */}
      <PowerMeter ratio={influence.ratio} verdict={influence.verdict} />

      {/* Content */}
      <div className="p-5">
        {/* Influence ratio */}
        <div className="text-center mb-4">
          <div className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
            {t("electoralInfluence")}
          </div>
          <div
            className={`text-3xl font-bold ${
              isKingmaker
                ? "text-red-600"
                : isSafeSeat
                  ? "text-slate-500"
                  : "text-amber-600"
            }`}
          >
            {influence.ratio.toFixed(1)}
            <span className="text-lg">x</span>
          </div>
        </div>

        {/* Key numbers */}
        <div className="grid grid-cols-2 gap-3 mb-4">
          <div className="bg-slate-50 rounded-lg p-3 text-center">
            <div className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
              {t("indianVoters")}
            </div>
            <div className="text-base font-bold text-slate-800 mt-0.5">
              {influence.indian_voters.toLocaleString()}
            </div>
          </div>
          <div
            className={`rounded-lg p-3 text-center border ${
              isKingmaker
                ? "bg-red-50 border-red-200"
                : isSafeSeat
                  ? "bg-slate-50 border-slate-200"
                  : "bg-amber-50 border-amber-200"
            }`}
          >
            <div
              className={`text-[10px] font-semibold uppercase tracking-wider ${
                isKingmaker
                  ? "text-red-400"
                  : isSafeSeat
                    ? "text-slate-400"
                    : "text-amber-400"
              }`}
            >
              {t("winningMargin")}
            </div>
            <div
              className={`text-base font-bold mt-0.5 ${
                isKingmaker
                  ? "text-red-700"
                  : isSafeSeat
                    ? "text-slate-800"
                    : "text-amber-700"
              }`}
            >
              {influence.winning_margin.toLocaleString()}
            </div>
          </div>
        </div>

        {/* Verdict badge */}
        <div
          className={`flex items-center justify-center gap-2 rounded-full py-2.5 px-4 ${config.bg} ${config.text} transition-colors`}
        >
          <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d={config.icon} strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <span className="text-sm font-semibold uppercase tracking-wide">
            {t(`verdict_${influence.verdict}`)}
          </span>
        </div>

        {/* Data source links */}
        {(constituencyCode || constituencyName) && (
          <div className="flex items-center justify-center gap-3 mt-4 text-[11px]">
            {constituencyCode && constituencyName && state && (
              <a
                href={`https://open.dosm.gov.my/dashboard/kawasanku/${encodeURIComponent(state.toLowerCase().replace(/\b\w/g, c => c.toUpperCase()))}/parlimen/${encodeURIComponent(constituencyCode.replace(/^(P)(\d)/, "$1.$2") + " " + constituencyName)}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-500 hover:text-blue-700 hover:underline"
              >
                DOSM Kawasanku
              </a>
            )}
            {constituencyName && (
              <>
                {constituencyCode && state && (
                  <span className="text-slate-300">|</span>
                )}
                <a
                  href={`https://en.wikipedia.org/wiki/${encodeURIComponent(constituencyName.replace(/ /g, "_"))}_(federal_constituency)`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-500 hover:text-blue-700 hover:underline"
                >
                  Wikipedia
                </a>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
