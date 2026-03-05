"use client";

const PAGE_SIZE_OPTIONS = [5, 10, 25];

interface PaginationBarProps {
  currentPage: number;
  totalPages: number;
  totalItems: number;
  pageSize: number;
  onPageChange: (page: number) => void;
  onPageSizeChange: (size: number) => void;
  /** Label for "Showing X-Y of Z" — receives { from, to, total } */
  showingLabel: (from: number, to: number, total: number) => string;
}

export default function PaginationBar({
  currentPage,
  totalPages,
  totalItems,
  pageSize,
  onPageChange,
  onPageSizeChange,
  showingLabel,
}: PaginationBarProps) {
  if (totalItems === 0) return null;

  const from = (currentPage - 1) * pageSize + 1;
  const to = Math.min(currentPage * pageSize, totalItems);
  const pages = getPageNumbers(currentPage, totalPages);

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 mt-6 text-sm">
      {/* Left: Show [select] Showing X-Y of Z results */}
      <div className="flex items-center gap-2 text-gray-500">
        <span>Show:</span>
        <select
          value={pageSize}
          onChange={(e) => onPageSizeChange(Number(e.target.value))}
          className="border border-gray-300 rounded px-1.5 py-0.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-primary-500"
        >
          {PAGE_SIZE_OPTIONS.map((size) => (
            <option key={size} value={size}>
              {size}
            </option>
          ))}
        </select>
        <span className="text-gray-400 ml-1">
          {showingLabel(from, to, totalItems)}
        </span>
      </div>

      {/* Right: < 1 2 3 ... 12 > */}
      {totalPages > 1 && (
        <nav aria-label="Pagination" className="flex items-center gap-1">
          <button
            onClick={() => onPageChange(currentPage - 1)}
            disabled={currentPage === 1}
            className="w-8 h-8 flex items-center justify-center rounded-lg transition-colors disabled:opacity-30 disabled:cursor-not-allowed text-gray-500 hover:bg-gray-100"
            aria-label="Previous page"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M10 12L6 8l4-4" />
            </svg>
          </button>

          {pages.map((page, i) =>
            page === "..." ? (
              <span key={`ellipsis-${i}`} className="w-8 h-8 flex items-center justify-center text-gray-400">
                ...
              </span>
            ) : (
              <button
                key={page}
                onClick={() => onPageChange(page as number)}
                className={`w-8 h-8 text-sm font-medium rounded-lg transition-colors ${
                  currentPage === page
                    ? "bg-amber-700 text-white"
                    : "text-gray-600 hover:bg-gray-100"
                }`}
              >
                {page}
              </button>
            )
          )}

          <button
            onClick={() => onPageChange(currentPage + 1)}
            disabled={currentPage === totalPages}
            className="w-8 h-8 flex items-center justify-center rounded-lg transition-colors disabled:opacity-30 disabled:cursor-not-allowed text-gray-500 hover:bg-gray-100"
            aria-label="Next page"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M6 4l4 4-4 4" />
            </svg>
          </button>
        </nav>
      )}
    </div>
  );
}

/** Generate page numbers with ellipsis for large page counts */
function getPageNumbers(current: number, total: number): (number | "...")[] {
  if (total <= 7) {
    return Array.from({ length: total }, (_, i) => i + 1);
  }

  const pages: (number | "...")[] = [1];

  if (current > 3) {
    pages.push("...");
  }

  const start = Math.max(2, current - 1);
  const end = Math.min(total - 1, current + 1);

  for (let i = start; i <= end; i++) {
    pages.push(i);
  }

  if (current < total - 2) {
    pages.push("...");
  }

  pages.push(total);
  return pages;
}
