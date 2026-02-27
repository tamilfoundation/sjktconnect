import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import ScorecardCard from "@/components/ScorecardCard";
import { Scorecard } from "@/lib/types";

const makeScorecard = (overrides: Partial<Scorecard> = {}): Scorecard => ({
  total_mentions: 12,
  substantive_mentions: 8,
  questions_asked: 3,
  commitments_made: 2,
  last_mention_date: "2026-02-15",
  ...overrides,
});

describe("ScorecardCard", () => {
  it("shows empty state when no scorecard", () => {
    render(<ScorecardCard scorecard={null} mpName="Test MP" />);
    expect(
      screen.getByText(/No parliamentary activity recorded/)
    ).toBeInTheDocument();
    expect(screen.getByText(/Test MP/)).toBeInTheDocument();
  });

  it("renders scorecard heading", () => {
    render(
      <ScorecardCard scorecard={makeScorecard()} mpName="Test MP" />
    );
    expect(
      screen.getByText("Parliament Watch Scorecard")
    ).toBeInTheDocument();
  });

  it("renders total mentions", () => {
    render(
      <ScorecardCard scorecard={makeScorecard()} mpName="Test MP" />
    );
    expect(screen.getByText("12")).toBeInTheDocument();
    expect(screen.getByText("Total Mentions")).toBeInTheDocument();
  });

  it("renders substantive mentions", () => {
    render(
      <ScorecardCard scorecard={makeScorecard()} mpName="Test MP" />
    );
    expect(screen.getByText("8")).toBeInTheDocument();
    expect(screen.getByText("Substantive")).toBeInTheDocument();
  });

  it("renders questions asked", () => {
    render(
      <ScorecardCard scorecard={makeScorecard()} mpName="Test MP" />
    );
    expect(screen.getByText("3")).toBeInTheDocument();
    expect(screen.getByText("Questions Asked")).toBeInTheDocument();
  });

  it("renders commitments", () => {
    render(
      <ScorecardCard scorecard={makeScorecard()} mpName="Test MP" />
    );
    expect(screen.getByText("2")).toBeInTheDocument();
    expect(screen.getByText("Commitments")).toBeInTheDocument();
  });

  it("formats last mention date", () => {
    render(
      <ScorecardCard scorecard={makeScorecard()} mpName="Test MP" />
    );
    expect(screen.getByText(/15 February 2026/)).toBeInTheDocument();
  });
});
