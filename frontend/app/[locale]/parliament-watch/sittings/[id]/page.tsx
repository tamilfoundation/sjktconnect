import { Metadata } from "next";
import { notFound } from "next/navigation";
import { getTranslations } from "next-intl/server";
import { Link } from "@/i18n/navigation";
import { fetchBrief, fetchBriefs } from "@/lib/api";

export const revalidate = 3600;

interface Props {
  params: Promise<{ id: string }>;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { id } = await params;
  const t = await getTranslations("parliamentWatch");
  const brief = await fetchBrief(Number(id));
  if (!brief) return { title: t("title") };
  return {
    title: brief.title,
    description: brief.summary_html.replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim().slice(0, 160),
  };
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleDateString("en-GB", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

export default async function BriefDetailPage({ params }: Props) {
  const { id } = await params;
  const t = await getTranslations("parliamentWatch");

  const brief = await fetchBrief(Number(id));
  if (!brief) notFound();

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
        <Link href="/parliament-watch/sittings" className="hover:text-primary-600 transition-colors">
          {t("sittingBriefs")}
        </Link>
        <svg className="w-4 h-4 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
        </svg>
        <span className="text-gray-900 font-medium">{formatDate(brief.sitting_date)}</span>
      </nav>

      {/* Header */}
      <header className="mb-8">
        <p className="text-sm font-medium text-primary-600 uppercase tracking-wide mb-2">
          {formatDate(brief.sitting_date)}
        </p>
        <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 leading-tight mb-3">
          {brief.title.replace(/\s*[—–-]\s*\d{1,2}\s+\w+\s+\d{4}$/, "")}
        </h1>
        <span className="inline-flex items-center gap-1 text-xs font-medium bg-primary-50 text-primary-700 px-2.5 py-1 rounded-full">
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          </svg>
          {brief.mention_count} {brief.mention_count === 1 ? "mention" : "mentions"}
        </span>
      </header>

      {/* Brief body — trusted HTML from our own backend API, not user-submitted */}
      <article
        className="prose prose-sm sm:prose-base max-w-none mb-12
          prose-headings:text-gray-900 prose-headings:font-semibold
          prose-h2:text-lg prose-h2:mt-8 prose-h2:mb-3
          prose-h3:text-base prose-h3:mt-5 prose-h3:mb-2
          prose-p:text-gray-700 prose-p:leading-relaxed
          prose-li:text-gray-700 prose-li:leading-relaxed
          prose-strong:text-gray-900
          prose-ul:my-2 prose-li:my-1
          prose-blockquote:border-l-primary-400 prose-blockquote:text-gray-600
          prose-a:text-primary-600 prose-a:no-underline hover:prose-a:underline"
        dangerouslySetInnerHTML={{ __html: brief.summary_html }}
      />

      {/* Back link */}
      <div className="border-t border-gray-200 pt-6">
        <Link
          href="/parliament-watch/sittings"
          className="inline-flex items-center gap-1 text-sm font-medium text-primary-600 hover:text-primary-700 transition-colors"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
          </svg>
          {t("backToSittingBriefs")}
        </Link>
      </div>
    </div>
  );
}
