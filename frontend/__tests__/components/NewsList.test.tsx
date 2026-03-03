import "@testing-library/jest-dom";
import { render, screen, fireEvent } from "@testing-library/react";
import NewsList from "@/components/NewsList";
import { NewsArticle } from "@/lib/types";

jest.mock("next-intl", () => ({
  useTranslations: () => (key: string, params?: Record<string, unknown>) => {
    if (params) return `${key}:${JSON.stringify(params)}`;
    return key;
  },
}));

jest.mock("@/i18n/navigation", () => ({
  Link: ({ children, href, ...props }: any) => <a href={href} {...props}>{children}</a>,
}));

jest.mock("@/components/NewsCard", () => {
  return function MockNewsCard({ article }: { article: NewsArticle }) {
    return <div data-testid={`news-card-${article.id}`}>{article.title}</div>;
  };
});

const mockArticles: NewsArticle[] = [
  {
    id: 1,
    title: "Article One",
    url: "https://example.com/1",
    source_name: "The Star",
    published_date: "2026-03-01T10:00:00Z",
    ai_summary: "Summary one.",
    sentiment: "POSITIVE",
    is_urgent: false,
    urgent_reason: "",
    mentioned_schools: [{ name: "SJK(T) Test", moe_code: "JBD0050" }],
    created_at: "2026-03-01T10:00:00Z",
  },
  {
    id: 2,
    title: "Article Two",
    url: "https://example.com/2",
    source_name: "Malaysiakini",
    published_date: "2026-02-15T08:00:00Z",
    ai_summary: "Summary two.",
    sentiment: "NEUTRAL",
    is_urgent: false,
    urgent_reason: "",
    mentioned_schools: [],
    created_at: "2026-02-15T08:00:00Z",
  },
];

describe("NewsList", () => {
  it("renders all articles", () => {
    render(<NewsList articles={mockArticles} totalCount={2} />);
    expect(screen.getByTestId("news-card-1")).toBeInTheDocument();
    expect(screen.getByTestId("news-card-2")).toBeInTheDocument();
  });

  it("renders tab buttons", () => {
    render(<NewsList articles={mockArticles} totalCount={2} />);
    expect(screen.getByText("tabAll")).toBeInTheDocument();
    expect(screen.getByText("tabBySchool")).toBeInTheDocument();
    expect(screen.getByText("tabGeneral")).toBeInTheDocument();
  });

  it("renders search input with correct placeholder", () => {
    render(<NewsList articles={mockArticles} totalCount={2} />);
    const input = screen.getByPlaceholderText("searchPlaceholder");
    expect(input).toBeInTheDocument();
  });

  it("shows subscribe CTA sidebar", () => {
    render(<NewsList articles={mockArticles} totalCount={2} />);
    expect(screen.getByText("subscribeCta")).toBeInTheDocument();
    expect(screen.getByText("subscribeDesc")).toBeInTheDocument();
    const subscribeLink = screen.getByText("subscribeButton");
    expect(subscribeLink.closest("a")).toHaveAttribute("href", "/subscribe");
  });

  it("shows empty state when no articles", () => {
    render(<NewsList articles={[]} totalCount={0} />);
    expect(screen.getByText("noArticles")).toBeInTheDocument();
  });

  it("filters to school articles when By School tab is clicked", () => {
    render(<NewsList articles={mockArticles} totalCount={2} />);

    fireEvent.click(screen.getByText("tabBySchool"));

    // Article 1 has mentioned_schools, Article 2 does not
    expect(screen.getByTestId("news-card-1")).toBeInTheDocument();
    expect(screen.queryByTestId("news-card-2")).not.toBeInTheDocument();
  });
});
