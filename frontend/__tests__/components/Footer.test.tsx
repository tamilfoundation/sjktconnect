import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import Footer from "@/components/Footer";

describe("Footer", () => {
  it("renders copyright text", () => {
    render(<Footer />);
    expect(screen.getByText(/Tamil Foundation Malaysia/)).toBeInTheDocument();
  });

  it("includes current year", () => {
    render(<Footer />);
    const year = new Date().getFullYear().toString();
    const matches = screen.getAllByText(new RegExp(year));
    expect(matches.length).toBeGreaterThan(0);
  });

  it("mentions data sources", () => {
    render(<Footer />);
    expect(
      screen.getByText(/MOE.*Parliament of Malaysia/)
    ).toBeInTheDocument();
  });

  it("has subscribe link", () => {
    render(<Footer />);
    const link = screen.getByRole("link", { name: /Subscribe to Intelligence Blast/ });
    expect(link).toHaveAttribute("href", "/subscribe");
  });
});
