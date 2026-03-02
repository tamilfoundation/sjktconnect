import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import NewsWatchSection from "@/components/NewsWatchSection";
import { NewsArticle } from "@/lib/types";

const makeArticle = (overrides: Partial<NewsArticle> = {}): NewsArticle => ({
  id: 1,
  title: "Tamil school gets new building",
  url: "https://example.com/article-1",
  source_name: "The Star",
  published_date: "2026-03-01T10:00:00Z",
  ai_summary: "New building for SJK(T) Ladang Bikam.",
  sentiment: "POSITIVE",
  is_urgent: false,
  urgent_reason: "",
  created_at: "2026-03-01T12:00:00Z",
  ...overrides,
});

describe("NewsWatchSection", () => {
  it("shows empty message when no articles", () => {
    render(<NewsWatchSection articles={[]} />);
    expect(screen.getByText(/no news articles yet/i)).toBeInTheDocument();
  });

  it("renders the News Watch heading", () => {
    render(<NewsWatchSection articles={[makeArticle()]} />);
    expect(screen.getByText("News Watch")).toBeInTheDocument();
  });

  it("renders article title as a link", () => {
    render(<NewsWatchSection articles={[makeArticle()]} />);
    const link = screen.getByRole("link", { name: /tamil school gets new building/i });
    expect(link).toHaveAttribute("href", "https://example.com/article-1");
    expect(link).toHaveAttribute("target", "_blank");
  });

  it("renders source name", () => {
    render(<NewsWatchSection articles={[makeArticle()]} />);
    expect(screen.getByText("The Star")).toBeInTheDocument();
  });

  it("renders AI summary", () => {
    render(<NewsWatchSection articles={[makeArticle()]} />);
    expect(screen.getByText(/new building for sjk/i)).toBeInTheDocument();
  });

  it("renders sentiment badge", () => {
    render(<NewsWatchSection articles={[makeArticle({ sentiment: "NEGATIVE" })]} />);
    expect(screen.getByText("Negative")).toBeInTheDocument();
  });

  it("renders urgent badge when flagged", () => {
    render(<NewsWatchSection articles={[makeArticle({ is_urgent: true })]} />);
    expect(screen.getByText("Urgent")).toBeInTheDocument();
  });

  it("does not render urgent badge when not flagged", () => {
    render(<NewsWatchSection articles={[makeArticle({ is_urgent: false })]} />);
    expect(screen.queryByText("Urgent")).not.toBeInTheDocument();
  });

  it("formats date in British English", () => {
    render(
      <NewsWatchSection
        articles={[makeArticle({ published_date: "2026-03-01T10:00:00Z" })]}
      />
    );
    expect(screen.getByText("1 March 2026")).toBeInTheDocument();
  });
});
