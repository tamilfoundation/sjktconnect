"use client";

/**
 * EnrolmentTrend — proper line chart of a school's student count over
 * the last 5+ MOE Risalah snapshots (2018 → current).
 *
 * X-axis: time-positioned (years 2018-2026, evenly spaced ticks).
 * Y-axis: value-scaled with horizontal gridlines + value labels.
 * Data points plotted at their ACTUAL year position (not evenly spaced
 * left-to-right) — so a 2025-only gap is visible.
 *
 * Line + fill colour conditional on overall trend:
 *   Δ ≥ 0 (stable / improving)  → emerald
 *   Δ <  0 (declining)          → rose
 *
 * No chart-lib dependency — inline SVG keeps the bundle small and the
 * component server-renderable.
 */

import { useTranslations, useLocale } from "next-intl";

interface SnapshotPoint {
  date: string;     // ISO YYYY-MM-DD
  students: number;
}

interface Props {
  history: SnapshotPoint[];
}

// 1:1 SVG aspect so the rendered card matches the height of the
// SchoolDetails card on the left column (~470px typical). Earlier 1.5:1
// (300x200) rendered too short alongside it. The extra vertical room
// also lets the line breathe and exposes the trend more clearly.
const W = 300;
const H = 300;
const PAD_L = 38;   // y-axis labels live here
const PAD_R = 14;
const PAD_T = 24;   // per-point value labels live here
const PAD_B = 30;   // x-axis labels live here

// X axis fixed range: discrete year slots from 2018 to 2026. Data
// points are positioned by their YEAR (not exact date) so the latest
// 2026 value sits on the 2026 tick.
const X_FIRST_YEAR = 2018;
const X_LAST_YEAR = 2026;

export default function EnrolmentTrend({ history }: Props) {
  const t = useTranslations("enrolmentTrend");
  const locale = useLocale();

  // Use the actual history as-is. No auto-append of today's date — the
  // April 2026 snapshot IS the current value, so an auto-appended "today"
  // would just stack a duplicate on the rightmost edge (owner feedback
  // after the v1 chart shipped: "ignore Jan 2026, align with 2026 tick").
  // For schools where the live `enrolment` has drifted away from the
  // latest snapshot but no fresh snapshot has been imported, the latest
  // snapshot still represents the most recently published MOE figure —
  // which is what we should plot.
  const pts: SnapshotPoint[] = [...history];

  if (pts.length < 2) return null;

  const innerW = W - PAD_L - PAD_R;
  const innerH = H - PAD_T - PAD_B;

  // Y axis: nice round bounds with ~4 gridlines.
  const values = pts.map((p) => p.students);
  const rawMin = Math.min(...values);
  const rawMax = Math.max(...values);
  const { yMin, yMax, yTicks } = computeYTicks(rawMin, rawMax);

  // X axis: yearly ticks 2018-2026, evenly spaced.
  const xTicks: number[] = [];
  for (let y = X_FIRST_YEAR; y <= X_LAST_YEAR; y++) xTicks.push(y);

  // Discrete-year positioning: each data point sits on its year's tick.
  const xOf = (iso: string) => {
    const y = parseInt(iso.slice(0, 4), 10);
    const frac = (y - X_FIRST_YEAR) / (X_LAST_YEAR - X_FIRST_YEAR);
    return PAD_L + Math.max(0, Math.min(1, frac)) * innerW;
  };
  const yOf = (v: number) =>
    PAD_T + innerH - ((v - yMin) / (yMax - yMin)) * innerH;

  const coords = pts.map((p) => ({ x: xOf(p.date), y: yOf(p.students), ...p }));
  const linePath = coords
    .map((c, i) => `${i === 0 ? "M" : "L"}${c.x.toFixed(1)},${c.y.toFixed(1)}`)
    .join(" ");
  const areaPath =
    `${linePath} L${coords[coords.length - 1].x.toFixed(1)},${(H - PAD_B).toFixed(1)} ` +
    `L${coords[0].x.toFixed(1)},${(H - PAD_B).toFixed(1)} Z`;

  const first = coords[0];
  const last = coords[coords.length - 1];
  const deltaPct =
    first.students > 0
      ? Math.round(((last.students - first.students) / first.students) * 100)
      : 0;
  const improving = deltaPct >= 0;
  const stroke = improving ? "rgb(5, 150, 105)" : "rgb(225, 29, 72)";   // emerald-600 / rose-600
  const fill = improving ? "rgba(5, 150, 105, 0.10)" : "rgba(225, 29, 72, 0.10)";
  const deltaTextClass = improving ? "text-emerald-600" : "text-rose-600";
  const deltaSign = improving ? "+" : "";

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className="flex items-center gap-2 px-6 py-4 border-b border-gray-100">
        <div className="w-1 h-5 bg-primary-600 rounded-full" />
        <h2 className="text-lg font-semibold text-gray-800">
          {t("title")}
        </h2>
      </div>
      <div className="p-4">
        <svg
          viewBox={`0 0 ${W} ${H}`}
          className="w-full"
          role="img"
          aria-label={t("ariaLabel", {
            from: yearOf(first.date),
            to: yearOf(last.date),
            fromCount: first.students,
            toCount: last.students,
          })}
        >
          {/* Y-axis gridlines + value labels */}
          {yTicks.map((v) => {
            const y = yOf(v);
            return (
              <g key={v}>
                <line
                  x1={PAD_L}
                  x2={W - PAD_R}
                  y1={y}
                  y2={y}
                  stroke="rgb(229, 231, 235)"
                  strokeWidth="0.5"
                />
                <text
                  x={PAD_L - 4}
                  y={y + 3}
                  fontSize="9"
                  fill="rgb(107, 114, 128)"
                  textAnchor="end"
                >
                  {v}
                </text>
              </g>
            );
          })}

          {/* X-axis year ticks */}
          {xTicks.map((y) => {
            const x = PAD_L + ((y - 2018) / (2026 - 2018)) * innerW;
            const showLabel = y % 2 === 0;   // every other year so labels don't crowd
            return (
              <g key={y}>
                <line
                  x1={x}
                  x2={x}
                  y1={H - PAD_B}
                  y2={H - PAD_B + 3}
                  stroke="rgb(156, 163, 175)"
                  strokeWidth="0.5"
                />
                {showLabel && (
                  <text
                    x={x}
                    y={H - PAD_B + 14}
                    fontSize="9"
                    fill="rgb(107, 114, 128)"
                    textAnchor="middle"
                  >
                    {y}
                  </text>
                )}
              </g>
            );
          })}

          {/* Data series */}
          <path d={areaPath} fill={fill} />
          <path
            d={linePath}
            fill="none"
            stroke={stroke}
            strokeWidth="1.8"
            strokeLinejoin="round"
            strokeLinecap="round"
          />

          {/* Data points + per-point value labels */}
          {coords.map((c, i) => (
            <g key={i}>
              <circle cx={c.x} cy={c.y} r={i === coords.length - 1 ? 3 : 2.3} fill={stroke}>
                <title>{`${c.date}: ${c.students.toLocaleString()}`}</title>
              </circle>
              <text
                x={c.x}
                y={c.y - 6}
                fontSize="9"
                fill="rgb(55, 65, 81)"
                textAnchor="middle"
                fontWeight="500"
              >
                {c.students}
              </text>
            </g>
          ))}
        </svg>

        <div className="flex items-center justify-between text-xs mt-2 px-1">
          <span className="text-gray-500">
            {t("source", {
              from: yearOf(first.date),
              to: formatMonthYear(last.date, locale),
            })}
          </span>
          <span className={`font-semibold ${deltaTextClass}`}>
            {deltaSign}{deltaPct}% {t("since", { year: yearOf(first.date) })}
          </span>
        </div>
      </div>
    </div>
  );
}

function yearOf(iso: string): string {
  return iso.slice(0, 4);
}

/**
 * Localised "Month YYYY" formatting via Intl.
 * Falls back to "YYYY-MM" if the locale tag isn't recognised.
 */
function formatMonthYear(iso: string, locale: string): string {
  const tag = locale === "ms" ? "ms-MY" : locale === "ta" ? "ta-MY" : "en-MY";
  try {
    return new Intl.DateTimeFormat(tag, { month: "long", year: "numeric" })
      .format(new Date(iso));
  } catch {
    return iso.slice(0, 7);
  }
}

/**
 * Pick nice round Y-axis bounds + ticks that bracket [min, max] with
 * ~4 horizontal gridlines.
 */
function computeYTicks(min: number, max: number): {
  yMin: number;
  yMax: number;
  yTicks: number[];
} {
  if (min === max) {
    // single-value series — give it some room
    const v = Math.max(min, 1);
    return { yMin: 0, yMax: Math.ceil(v * 1.5), yTicks: [0, Math.ceil(v * 1.5)] };
  }
  const range = max - min;
  // pick a step that gives 3-5 gridlines
  const niceSteps = [1, 2, 5, 10, 20, 25, 50, 100, 200, 250, 500, 1000];
  let step = niceSteps[0];
  for (const s of niceSteps) {
    if (range / s <= 5) { step = s; break; }
  }
  const yMin = Math.floor(min / step) * step;
  const yMax = Math.ceil(max / step) * step;
  const yTicks: number[] = [];
  for (let v = yMin; v <= yMax; v += step) yTicks.push(v);
  return { yMin, yMax, yTicks };
}
