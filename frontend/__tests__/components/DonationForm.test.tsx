import "@testing-library/jest-dom";
import { render, screen, fireEvent } from "@testing-library/react";
import DonationForm from "@/components/DonationForm";

describe("DonationForm", () => {
  it("renders preset amount buttons", () => {
    render(<DonationForm />);

    expect(screen.getByText("RM 10")).toBeInTheDocument();
    expect(screen.getByText("RM 50")).toBeInTheDocument();
    expect(screen.getByText("RM 100")).toBeInTheDocument();
    expect(screen.getByText("RM 250")).toBeInTheDocument();
  });

  it("renders donor info fields", () => {
    render(<DonationForm />);

    expect(screen.getByPlaceholderText("Your name")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Your email")).toBeInTheDocument();
    expect(
      screen.getByPlaceholderText("Phone number (optional)")
    ).toBeInTheDocument();
    expect(
      screen.getByPlaceholderText("Leave a message (optional)")
    ).toBeInTheDocument();
  });

  it("renders custom amount input", () => {
    render(<DonationForm />);

    expect(
      screen.getByPlaceholderText("Or enter a custom amount")
    ).toBeInTheDocument();
  });

  it("submit button disabled when form incomplete", () => {
    render(<DonationForm />);

    const submitButton = screen.getByRole("button", { name: /Donate/i });
    expect(submitButton).toBeDisabled();
  });

  it("submit button disabled with amount but no name", () => {
    render(<DonationForm />);

    fireEvent.click(screen.getByText("RM 50"));
    fireEvent.change(screen.getByPlaceholderText("Your email"), {
      target: { value: "test@example.com" },
    });

    const submitButton = screen.getByRole("button", { name: /Donate/i });
    expect(submitButton).toBeDisabled();
  });

  it("submit button disabled with amount but no email", () => {
    render(<DonationForm />);

    fireEvent.click(screen.getByText("RM 50"));
    fireEvent.change(screen.getByPlaceholderText("Your name"), {
      target: { value: "Test User" },
    });

    const submitButton = screen.getByRole("button", { name: /Donate/i });
    expect(submitButton).toBeDisabled();
  });

  it("submit button enabled when form is complete", () => {
    render(<DonationForm />);

    fireEvent.click(screen.getByText("RM 100"));
    fireEvent.change(screen.getByPlaceholderText("Your name"), {
      target: { value: "Test User" },
    });
    fireEvent.change(screen.getByPlaceholderText("Your email"), {
      target: { value: "test@example.com" },
    });

    const submitButton = screen.getByRole("button", { name: /Donate/i });
    expect(submitButton).toBeEnabled();
  });

  it("shows amount selection label", () => {
    render(<DonationForm />);

    expect(screen.getByText("Select an amount (RM)")).toBeInTheDocument();
  });
});
