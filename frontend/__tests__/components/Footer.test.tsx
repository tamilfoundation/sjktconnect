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

  it("has platform links", () => {
    render(<Footer />);
    expect(screen.getByText("Platform")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /School Map/ })).toHaveAttribute(
      "href",
      "/"
    );
    expect(
      screen.getByRole("link", { name: /Subscribe/ })
    ).toHaveAttribute("href", "/subscribe");
  });

  it("has legal links", () => {
    render(<Footer />);
    expect(screen.getByText("Legal")).toBeInTheDocument();
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
