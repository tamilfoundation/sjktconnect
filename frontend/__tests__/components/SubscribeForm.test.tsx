import "@testing-library/jest-dom";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import SubscribeForm from "@/components/SubscribeForm";

const mockSubscribe = jest.fn();
jest.mock("@/lib/api", () => ({
  subscribe: (...args: unknown[]) => mockSubscribe(...args),
}));

beforeEach(() => {
  mockSubscribe.mockClear();
});

describe("SubscribeForm", () => {
  it("renders email input and subscribe button", () => {
    render(<SubscribeForm />);
    expect(screen.getByLabelText(/Email address/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Subscribe/ })).toBeInTheDocument();
  });

  it("renders name and organisation fields", () => {
    render(<SubscribeForm />);
    expect(screen.getByLabelText(/Name/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Organisation/)).toBeInTheDocument();
  });

  it("renders category descriptions", () => {
    render(<SubscribeForm />);
    expect(screen.getByText("Parliament Watch")).toBeInTheDocument();
    expect(screen.getByText("News Watch")).toBeInTheDocument();
    expect(screen.getByText("Monthly Intelligence Blast")).toBeInTheDocument();
  });

  it("shows success message after subscribing", async () => {
    mockSubscribe.mockResolvedValueOnce({
      email: "user@example.com",
      name: "Test User",
      organisation: "",
      is_active: true,
      subscribed_at: "2026-03-01T00:00:00Z",
      preferences: {
        PARLIAMENT_WATCH: true,
        NEWS_WATCH: true,
        MONTHLY_BLAST: true,
      },
    });

    render(<SubscribeForm />);
    fireEvent.change(screen.getByLabelText(/Email address/), {
      target: { value: "user@example.com" },
    });
    fireEvent.change(screen.getByLabelText(/Name/), {
      target: { value: "Test User" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Subscribe/ }));

    await waitFor(() => {
      expect(screen.getByText(/You're subscribed!/)).toBeInTheDocument();
    });
    expect(screen.getByText(/user@example.com/)).toBeInTheDocument();
  });

  it("calls subscribe with all fields", async () => {
    mockSubscribe.mockResolvedValueOnce({
      email: "user@example.com",
      name: "Test",
      organisation: "PIBG",
      is_active: true,
      subscribed_at: "2026-03-01T00:00:00Z",
      preferences: {},
    });

    render(<SubscribeForm />);
    fireEvent.change(screen.getByLabelText(/Email address/), {
      target: { value: "user@example.com" },
    });
    fireEvent.change(screen.getByLabelText(/Name/), {
      target: { value: "Test" },
    });
    fireEvent.change(screen.getByLabelText(/Organisation/), {
      target: { value: "PIBG" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Subscribe/ }));

    await waitFor(() => {
      expect(mockSubscribe).toHaveBeenCalledWith({
        email: "user@example.com",
        name: "Test",
        organisation: "PIBG",
      });
    });
  });

  it("shows error message on failure", async () => {
    mockSubscribe.mockRejectedValueOnce(new Error("Server error. Please try again."));

    render(<SubscribeForm />);
    fireEvent.change(screen.getByLabelText(/Email address/), {
      target: { value: "user@example.com" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Subscribe/ }));

    await waitFor(() => {
      expect(screen.getByText(/Server error/)).toBeInTheDocument();
    });
  });

  it("disables button while loading", async () => {
    mockSubscribe.mockImplementation(
      () => new Promise((resolve) => setTimeout(resolve, 1000))
    );

    render(<SubscribeForm />);
    fireEvent.change(screen.getByLabelText(/Email address/), {
      target: { value: "user@example.com" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Subscribe/ }));

    await waitFor(() => {
      expect(screen.getByText("Subscribing...")).toBeInTheDocument();
    });
  });

  it("shows note about managing preferences", () => {
    render(<SubscribeForm />);
    expect(
      screen.getByText(/All categories are enabled by default/)
    ).toBeInTheDocument();
  });
});
