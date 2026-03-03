import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import NewsCard from "@/components/NewsCard";
import { NewsArticle } from "@/lib/types";

jest.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key,
}));

jest.mock("@/i18n/navigation", () => ({
  Link: ({ children, href, ...props }: any) => <a href={href} {...props}>{children}</a>,
}));

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
  mentioned_schools: [],
  created_at: "2026-03-01T12:00:00Z",
  ...overrides,
});

describe("NewsCard", () => {
  it("renders article title as link with correct href", () => {
    render(<NewsCard article={makeArticle()} />);
    const link = screen.getByRole("link", { name: /tamil school gets new building/i });
    expect(link).toHaveAttribute("href", "https://example.com/article-1");
    expect(link).toHaveAttribute("target", "_blank");
  });

  it("renders source name and formatted date", () => {
    render(<NewsCard article={makeArticle({ published_date: "2026-03-01T10:00:00Z" })} />);
    expect(screen.getByText("The Star")).toBeInTheDocument();
    expect(screen.getByText("1 March 2026")).toBeInTheDocument();
  });

  it("renders AI summary", () => {
    render(<NewsCard article={makeArticle()} />);
    expect(screen.getByText(/new building for sjk/i)).toBeInTheDocument();
  });

  it("renders sentiment badge", () => {
    render(<NewsCard article={makeArticle({ sentiment: "POSITIVE" })} />);
    expect(screen.getByText("Positive")).toBeInTheDocument();
  });

  it("renders school chips as links", () => {
    render(
      <NewsCard
        article={makeArticle({
          mentioned_schools: [
            { name: "SJK(T) Ladang Bikam", moe_code: "ABC1234" },
            { name: "SJK(T) Kuala Lumpur", moe_code: "XYZ5678" },
          ],
        })}
      />
    );
    const bikamLink = screen.getByRole("link", { name: /ladang bikam/i });
    expect(bikamLink).toHaveAttribute("href", "/school/ABC1234");
    const klLink = screen.getByRole("link", { name: /kuala lumpur/i });
    expect(klLink).toHaveAttribute("href", "/school/XYZ5678");
  });

  it("renders URGENT badge when is_urgent is true", () => {
    render(<NewsCard article={makeArticle({ is_urgent: true })} />);
    expect(screen.getByText("urgent")).toBeInTheDocument();
  });

  it("does NOT render URGENT badge when not urgent", () => {
    render(<NewsCard article={makeArticle({ is_urgent: false })} />);
    expect(screen.queryByText("urgent")).not.toBeInTheDocument();
  });
});
