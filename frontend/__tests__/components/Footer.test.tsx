import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import Footer from "@/components/Footer";

describe("Footer", () => {
  it("renders copyright text", () => {
    render(<Footer />);
    expect(screen.getByText(/All rights reserved/)).toBeInTheDocument();
  });

  it("includes current year", () => {
    render(<Footer />);
    const year = new Date().getFullYear().toString();
    const matches = screen.getAllByText(new RegExp(year));
    expect(matches.length).toBeGreaterThan(0);
  });

  it("renders all 4 column headings", () => {
    render(<Footer />);
    expect(screen.getByText("Explore")).toBeInTheDocument();
    expect(screen.getByText("Intelligence")).toBeInTheDocument();
    expect(screen.getByText("Resources")).toBeInTheDocument();
    const aboutHeadings = screen.getAllByText("About");
    expect(aboutHeadings.length).toBeGreaterThanOrEqual(1);
  });

  it("has Explore links", () => {
    render(<Footer />);
    expect(
      screen.getByRole("link", { name: /School Map/ })
    ).toHaveAttribute("href", "/");
    expect(
      screen.getByRole("link", { name: /Constituencies/ })
    ).toHaveAttribute("href", "/constituencies");
    expect(
      screen.getByRole("link", { name: /About Tamil Schools/ })
    ).toHaveAttribute("href", "/about-tamil-schools");
  });

  it("has Intelligence links", () => {
    render(<Footer />);
    expect(
      screen.getByRole("link", { name: /News & Reports/ })
    ).toHaveAttribute("href", "/news");
    expect(
      screen.getByRole("link", { name: /Issues/ })
    ).toHaveAttribute("href", "/issues");
    expect(
      screen.getByRole("link", { name: /Parliament Watch/ })
    ).toHaveAttribute("href", "/parliament-watch");
  });

  it("has Resources links", () => {
    render(<Footer />);
    expect(
      screen.getByRole("link", { name: /PTA Toolkit/ })
    ).toHaveAttribute("href", "/resources/pta-toolkit");
    expect(
      screen.getByRole("link", { name: /LPS Toolkit/ })
    ).toHaveAttribute("href", "/resources/lps-toolkit");
    expect(
      screen.getByRole("link", { name: /Data & Downloads/ })
    ).toHaveAttribute("href", "/data");
    expect(
      screen.getByRole("link", { name: /FAQ/ })
    ).toHaveAttribute("href", "/faq");
  });

  it("has About & Legal links", () => {
    render(<Footer />);
    expect(
      screen.getByRole("link", { name: /^About$/ })
    ).toHaveAttribute("href", "/about");
    expect(
      screen.getByRole("link", { name: /Contact/ })
    ).toHaveAttribute("href", "/contact");
    expect(
      screen.getByRole("link", { name: /Subscribe/ })
    ).toHaveAttribute("href", "/subscribe");
    expect(
      screen.getByRole("link", { name: /Donate/ })
    ).toHaveAttribute("href", "/donate");
  });

  it("has legal links", () => {
    render(<Footer />);
    expect(
      screen.getByRole("link", { name: /Privacy Policy/ })
    ).toHaveAttribute("href", "/privacy");
    expect(
      screen.getByRole("link", { name: /Terms of Service/ })
    ).toHaveAttribute("href", "/terms");
    expect(
      screen.getByRole("link", { name: /Cookie Policy/ })
    ).toHaveAttribute("href", "/cookies");
  });

  it("has social media links", () => {
    render(<Footer />);
    expect(screen.getByLabelText("Facebook")).toBeInTheDocument();
    expect(screen.getByLabelText("X (Twitter)")).toBeInTheDocument();
  });
});
