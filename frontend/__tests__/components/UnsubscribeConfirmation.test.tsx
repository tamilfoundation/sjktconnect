import "@testing-library/jest-dom";
import { render, screen, waitFor } from "@testing-library/react";
import UnsubscribeConfirmation from "@/components/UnsubscribeConfirmation";

const mockUnsubscribe = jest.fn();
jest.mock("@/lib/api", () => ({
  unsubscribe: (...args: unknown[]) => mockUnsubscribe(...args),
}));

beforeEach(() => {
  mockUnsubscribe.mockClear();
});

describe("UnsubscribeConfirmation", () => {
  it("shows loading state initially", () => {
    mockUnsubscribe.mockImplementation(
      () => new Promise(() => {})
    );
    render(<UnsubscribeConfirmation token="test-token" />);
    expect(screen.getByText(/Processing your request/)).toBeInTheDocument();
  });

  it("shows success after unsubscribing", async () => {
    mockUnsubscribe.mockResolvedValueOnce({
      detail: "You have been unsubscribed.",
      email: "user@example.com",
    });

    render(<UnsubscribeConfirmation token="valid-token" />);

    await waitFor(() => {
      expect(screen.getByText("Unsubscribed")).toBeInTheDocument();
    });
    expect(screen.getByText(/user@example.com/)).toBeInTheDocument();
  });

  it("calls unsubscribe API with token", async () => {
    mockUnsubscribe.mockResolvedValueOnce({
      detail: "You have been unsubscribed.",
      email: "user@example.com",
    });

    render(<UnsubscribeConfirmation token="my-token-123" />);

    await waitFor(() => {
      expect(mockUnsubscribe).toHaveBeenCalledWith("my-token-123");
    });
  });

  it("shows error for invalid token", async () => {
    mockUnsubscribe.mockRejectedValueOnce(
      new Error("Invalid unsubscribe link.")
    );

    render(<UnsubscribeConfirmation token="bad-token" />);

    await waitFor(() => {
      expect(screen.getByText(/Unable to unsubscribe/)).toBeInTheDocument();
    });
    expect(screen.getByText(/Invalid unsubscribe link/)).toBeInTheDocument();
  });

  it("shows re-subscribe link after success", async () => {
    mockUnsubscribe.mockResolvedValueOnce({
      detail: "You have been unsubscribed.",
      email: "user@example.com",
    });

    render(<UnsubscribeConfirmation token="valid-token" />);

    await waitFor(() => {
      expect(screen.getByText("Unsubscribed")).toBeInTheDocument();
    });
    const link = screen.getByRole("link", { name: /Re-subscribe here/ });
    expect(link).toHaveAttribute("href", "/subscribe");
  });
});
