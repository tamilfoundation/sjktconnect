import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import HeroSection from "@/components/HeroSection";

describe("HeroSection", () => {
  const defaultProps = {
    totalSchools: 528,
    states: 12,
    constituencies: 150,
  };

  it("renders the headline", () => {
    render(<HeroSection {...defaultProps} />);
    expect(
      screen.getByText("Every Tamil School in Malaysia")
    ).toBeInTheDocument();
  });

  it("renders the subheadline", () => {
    render(<HeroSection {...defaultProps} />);
    expect(
      screen.getByText("Tracked. Connected. Heard.")
    ).toBeInTheDocument();
  });

  it("renders CTA buttons", () => {
    render(<HeroSection {...defaultProps} />);
    expect(screen.getByText("Find Your School")).toBeInTheDocument();
    expect(screen.getByText("Subscribe to Intelligence")).toBeInTheDocument();
  });

  it("renders stat cards with correct values", () => {
    render(<HeroSection {...defaultProps} />);
    expect(screen.getByText("528")).toBeInTheDocument();
    expect(screen.getByText("12")).toBeInTheDocument();
    expect(screen.getByText("150")).toBeInTheDocument();
  });

  it("renders stat labels", () => {
    render(<HeroSection {...defaultProps} />);
    expect(screen.getByText("Schools")).toBeInTheDocument();
    expect(screen.getByText("States")).toBeInTheDocument();
    expect(screen.getByText("Constituencies")).toBeInTheDocument();
  });
});
