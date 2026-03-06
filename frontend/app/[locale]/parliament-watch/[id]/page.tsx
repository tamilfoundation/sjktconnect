import { Metadata } from "next";
import { notFound } from "next/navigation";
import { getTranslations } from "next-intl/server";
import { Link } from "@/i18n/navigation";
import { fetchMeetingReport, fetchMeetingReports } from "@/lib/api";
import ReportShareBar from "@/components/ReportShareBar";

export const revalidate = 3600;

interface Props {
  params: Promise<{ id: string }>;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { id } = await params;
  const t = await getTranslations("parliamentWatch");
  const report = await fetchMeetingReport(Number(id));
  if (!report) return { title: t("title") };
  return {
    title: t("reportTitle", { name: report.short_name }),
    description: report.executive_summary?.replace(/<[^>]*>/g, "").slice(0, 160) || "",
  };
}

function formatDateRange(start: string, end: string): string {
  const s = new Date(start);
  const e = new Date(end);
  const opts: Intl.DateTimeFormatOptions = { day: "numeric", month: "short", year: "numeric" };
  return `${s.toLocaleDateString("en-GB", opts)} – ${e.toLocaleDateString("en-GB", opts)}`;
}

/**
 * Extract headline from the report HTML (first h2 that isn't a section heading).
 */
function extractHeadline(html: string): string | null {
  const match = html.match(/<h2[^>]*>(.*?)<\/h2>/i);
  if (!match) return null;
  const text = match[1].replace(/<[^>]*>/g, "").trim();
  const sectionHeadings = ["Key Findings", "MP Scorecard", "Executive Responses", "Policy Signals", "What to Watch"];
  if (sectionHeadings.some(h => text.includes(h))) return null;
  return text;
}

export default async function MeetingReportPage({ params }: Props) {
  const { id } = await params;
  const t = await getTranslations("parliamentWatch");

  const [report, allReports] = await Promise.all([
    fetchMeetingReport(Number(id)),
    fetchMeetingReports(),
  ]);

  if (!report || !report.report_html) notFound();

  // Find prev/next meeting
  const currentIndex = allReports.findIndex(r => r.id === report.id);
  const prevMeeting = currentIndex < allReports.length - 1 ? allReports[currentIndex + 1] : null;
  const nextMeeting = currentIndex > 0 ? allReports[currentIndex - 1] : null;

  const headline = extractHeadline(report.report_html);

  // Strip the headline h2 from the report body if we're showing it above
  let reportBody = report.report_html;
  if (headline) {
    reportBody = reportBody.replace(/<h2[^>]*>.*?<\/h2>/i, "");
  }

  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const reportUrl = `https://tamilschool.org/parliament-watch/${report.id}`;

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-2 text-sm text-gray-500 mb-6">
        <Link href="/parliament-watch" className="hover:text-primary-600 transition-colors">
          {t("backToParliamentWatch")}
        </Link>
        <svg className="w-4 h-4 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
        </svg>
        <span className="text-gray-900 font-medium">{report.short_name}</span>
      </nav>

      {/* Report Header */}
      <header className="mb-8">
        <p className="text-sm font-medium text-primary-600 uppercase tracking-wide mb-2">
          {formatDateRange(report.start_date, report.end_date)}
        </p>
        {headline ? (
          <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 leading-tight mb-3">
            {headline}
          </h1>
        ) : (
          <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 leading-tight mb-3">
            {report.short_name}
          </h1>
        )}
        <div className="flex flex-wrap gap-2 mb-4">
          <span className="inline-flex items-center gap-1 text-xs font-medium bg-blue-50 text-blue-700 px-2.5 py-1 rounded-full">
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
            {report.sitting_count} sittings tracked
          </span>
          <span className="inline-flex items-center gap-1 text-xs font-medium bg-primary-50 text-primary-700 px-2.5 py-1 rounded-full">
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
            {report.total_mentions} mentions
          </span>
        </div>

        {/* Share bar */}
        <ReportShareBar
          reportUrl={reportUrl}
          socialText={report.social_post_text}
          downloadUrl={`${API_URL}/api/v1/meetings/${report.id}/download/`}
        />
      </header>

      {/* Editorial illustration */}
      {report.illustration_url && (
        <div className="flex justify-center mb-8">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={report.illustration_url}
            alt={`Editorial illustration for ${report.short_name}`}
            className="max-w-xs rounded-lg border border-gray-200 shadow-sm"
          />
        </div>
      )}

      {/* Report body — trusted HTML from our own backend API */}
      <article
        className="prose prose-sm sm:prose-base max-w-none mb-12
          prose-headings:text-gray-900 prose-headings:font-semibold
          prose-h2:text-lg prose-h2:mt-8 prose-h2:mb-3
          prose-h3:text-base prose-h3:mt-5 prose-h3:mb-2
          prose-p:text-gray-700 prose-p:leading-relaxed
          prose-li:text-gray-700 prose-li:leading-relaxed
          prose-strong:text-gray-900
          prose-ul:my-2 prose-li:my-1
          prose-table:text-sm prose-th:text-left prose-th:px-3 prose-th:py-2
          prose-td:px-3 prose-td:py-2 prose-table:border-collapse
          prose-th:bg-gray-50 prose-th:border-b prose-th:border-gray-200
          prose-td:border-b prose-td:border-gray-100
          prose-a:text-primary-600 prose-a:no-underline hover:prose-a:underline"
        dangerouslySetInnerHTML={{ __html: reportBody }}
      />

      {/* Previous / Next Navigation */}
      <nav className="grid grid-cols-1 sm:grid-cols-2 gap-4 border-t border-gray-200 pt-8">
        {prevMeeting ? (
          <Link
            href={`/parliament-watch/${prevMeeting.id}`}
            className="flex flex-col p-4 rounded-xl border border-gray-200 hover:border-primary-300 hover:shadow-sm transition-all"
          >
            <span className="text-xs text-gray-400 mb-1">&larr; {t("previousMeeting")}</span>
            <span className="text-sm font-semibold text-gray-900">{prevMeeting.short_name}</span>
          </Link>
        ) : (
          <div />
        )}
        {nextMeeting ? (
          <Link
            href={`/parliament-watch/${nextMeeting.id}`}
            className="flex flex-col items-end p-4 rounded-xl border border-gray-200 hover:border-primary-300 hover:shadow-sm transition-all text-right"
          >
            <span className="text-xs text-gray-400 mb-1">{t("nextMeeting")} &rarr;</span>
            <span className="text-sm font-semibold text-gray-900">{nextMeeting.short_name}</span>
          </Link>
        ) : (
          <div />
        )}
      </nav>
    </div>
  );
}
