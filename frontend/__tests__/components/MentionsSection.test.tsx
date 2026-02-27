import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import MentionsSection from "@/components/MentionsSection";
import { SchoolMention } from "@/lib/types";

const makeMention = (
  overrides: Partial<SchoolMention> = {}
): SchoolMention => ({
  sitting_date: "2026-02-01",
  mp_name: "YB Test MP",
  mp_constituency: "Segamat",
  mp_party: "BN",
  mention_type: "question",
  significance: 3,
  sentiment: "positive",
  ai_summary: "MP asked about school facilities",
  verbatim_quote: "SJK(T) Ladang Bikam memerlukan...",
  ...overrides,
});

describe("MentionsSection", () => {
  it("shows empty message when no mentions", () => {
    render(<MentionsSection mentions={[]} />);
    expect(
      screen.getByText(/No parliamentary mentions found/)
    ).toBeInTheDocument();
  });

  it("renders the Parliament Watch heading", () => {
    render(<MentionsSection mentions={[]} />);
    expect(screen.getByText("Parliament Watch")).toBeInTheDocument();
  });

  it("renders mention with MP name", () => {
    render(<MentionsSection mentions={[makeMention()]} />);
    expect(screen.getByText("YB Test MP")).toBeInTheDocument();
  });

  it("renders mention party badge", () => {
    render(<MentionsSection mentions={[makeMention()]} />);
    expect(screen.getByText("BN")).toBeInTheDocument();
  });

  it("renders AI summary", () => {
    render(<MentionsSection mentions={[makeMention()]} />);
    expect(
      screen.getByText("MP asked about school facilities")
    ).toBeInTheDocument();
  });

  it("renders significance badge", () => {
    render(<MentionsSection mentions={[makeMention({ significance: 4 })]} />);
    expect(screen.getByText("Significance: 4/5")).toBeInTheDocument();
  });

  it("formats date in British English", () => {
    render(
      <MentionsSection mentions={[makeMention({ sitting_date: "2026-02-01" })]} />
    );
    expect(screen.getByText(/1 February 2026/)).toBeInTheDocument();
  });
});
