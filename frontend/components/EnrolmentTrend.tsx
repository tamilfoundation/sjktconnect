"use client";

/**
 * EnrolmentTrend — compact SVG sparkline of a school's student count over
 * the last 5+ MOE Risalah snapshots (2018 → current). Renders nothing when
 * the api returns no history (legacy or yet-to-import schools).
 *
 * No chart-lib dependency — inline SVG keeps the bundle small and the
 * component server-renderable.
 */

import { useTranslations } from "next-intl";

interface SnapshotPoint {
  date: string;     // ISO YYYY-MM-DD
  students: number;
}

interface Props {
  history: SnapshotPoint[];
  currentStudents: number;
}

const W = 220;
const H = 56;
const PAD_X = 14;
const PAD_Y = 6;

export default function EnrolmentTrend({ history, currentStudents }: Props) {
  const t = useTranslations("enrolmentTrend");

  // Append today's live count as the rightmost point if not already covered
  // by the latest snapshot (within 30 days). Lets the sparkline always end
  // on "what the page shows above".
  const pts: SnapshotPoint[] = [...history];
  const latest = pts[pts.length - 1];
  const today = new Date().toISOString().slice(0, 10);
  if (!latest || daysBetween(latest.date, today) > 30) {
    pts.push({ date: today, students: currentStudents });
  }

  if (pts.length < 2) return null;

  const values = pts.map((p) => p.students);
  const minV = Math.min(...values);
  const maxV = Math.max(...values);
  const range = Math.max(1, maxV - minV);

  const innerW = W - PAD_X * 2;
  const innerH = H - PAD_Y * 2;

  const coords = pts.map((p, i) => {
    const x = PAD_X + (i / (pts.length - 1)) * innerW;
    const y = PAD_Y + innerH - ((p.students - minV) / range) * innerH;
    return { x, y, ...p };
  });

  const path = coords.map((c, i) => `${i === 0 ? "M" : "L"}${c.x.toFixed(1)},${c.y.toFixed(1)}`).join(" ");
  const areaPath = `${path} L${coords[coords.length - 1].x.toFixed(1)},${(H - PAD_Y).toFixed(1)} L${coords[0].x.toFixed(1)},${(H - PAD_Y).toFixed(1)} Z`;

  const first = coords[0];
  const last = coords[coords.length - 1];
  const deltaPct = first.students > 0 ? Math.round(((last.students - first.students) / first.students) * 100) : 0;
  const deltaColor = deltaPct > 0 ? "text-emerald-600" : deltaPct < 0 ? "text-rose-600" : "text-gray-500";
  const deltaSign = deltaPct > 0 ? "+" : "";

  return (
    <div className="mt-2">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="w-full h-12"
        role="img"
        aria-label={t("ariaLabel", {
          from: yearOf(first.date),
          to: yearOf(last.date),
          fromCount: first.students,
          toCount: last.students,
        })}
      >
        <path d={areaPath} fill="rgba(79, 70, 229, 0.10)" />
        <path d={path} fill="none" stroke="rgb(79, 70, 229)" strokeWidth="1.5" strokeLinejoin="round" strokeLinecap="round" />
        {coords.map((c, i) => (
          <circle key={i} cx={c.x} cy={c.y} r={i === coords.length - 1 ? 2.5 : 1.5} fill="rgb(79, 70, 229)">
            <title>{`${c.date}: ${c.students.toLocaleString()}`}</title>
          </circle>
        ))}
      </svg>
      <div className="flex items-center justify-between text-[10px] text-gray-500 mt-0.5 px-1">
        <span>{yearOf(first.date)}</span>
        <span className={`font-medium ${deltaColor}`}>
          {deltaSign}{deltaPct}% {t("since", { year: yearOf(first.date) })}
        </span>
        <span>{yearOf(last.date)}</span>
      </div>
    </div>
  );
}

function daysBetween(a: string, b: string): number {
  return Math.abs(
    Math.round((new Date(a).getTime() - new Date(b).getTime()) / 86400000),
  );
}

function yearOf(iso: string): string {
  return iso.slice(0, 4);
}
