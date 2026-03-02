import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import ClaimButton from "@/components/ClaimButton";

describe("ClaimButton", () => {
  it("renders the claim link", () => {
    render(<ClaimButton moeCode="JBD0050" />);
    expect(
      screen.getByRole("link", { name: /Claim This Page/i })
    ).toBeInTheDocument();
  });

  it("links to claim page with school code", () => {
    render(<ClaimButton moeCode="JBD0050" />);
    const link = screen.getByRole("link", { name: /Claim This Page/i });
    expect(link).toHaveAttribute("href", "/claim/?school=JBD0050");
  });

  it("shows moe.edu.my requirement", () => {
    render(<ClaimButton moeCode="JBD0050" />);
    expect(screen.getByText(/moe.edu.my/)).toBeInTheDocument();
  });

  it("shows the question prompt", () => {
    render(<ClaimButton moeCode="JBD0050" />);
    expect(
      screen.getByText(/Are you from this school/)
    ).toBeInTheDocument();
  });
});
