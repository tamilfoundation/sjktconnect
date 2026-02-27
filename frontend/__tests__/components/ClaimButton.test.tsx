import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import ClaimButton from "@/components/ClaimButton";

describe("ClaimButton", () => {
  it("renders the claim button", () => {
    render(<ClaimButton moeCode="JBD0050" />);
    expect(
      screen.getByRole("button", { name: /Claim/i })
    ).toBeInTheDocument();
  });

  it("shows coming soon text", () => {
    render(<ClaimButton moeCode="JBD0050" />);
    expect(screen.getByText(/Coming soon/)).toBeInTheDocument();
  });

  it("button is disabled", () => {
    render(<ClaimButton moeCode="JBD0050" />);
    expect(screen.getByRole("button", { name: /Claim/i })).toBeDisabled();
  });

  it("shows the question prompt", () => {
    render(<ClaimButton moeCode="JBD0050" />);
    expect(
      screen.getByText(/Are you from this school/)
    ).toBeInTheDocument();
  });
});
