import "@testing-library/jest-dom";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import ClaimForm from "@/components/ClaimForm";

const mockRequestMagicLink = jest.fn();
jest.mock("@/lib/api", () => ({
  requestMagicLink: (...args: unknown[]) => mockRequestMagicLink(...args),
}));

beforeEach(() => {
  mockRequestMagicLink.mockClear();
});

describe("ClaimForm", () => {
  it("renders email input and submit button", () => {
    render(<ClaimForm />);
    expect(screen.getByLabelText(/School email address/)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Send Verification Link/ })
    ).toBeInTheDocument();
  });

  it("pre-fills email when moeCode is provided", () => {
    render(<ClaimForm moeCode="JBD0050" />);
    const input = screen.getByLabelText(/School email address/) as HTMLInputElement;
    expect(input.value).toBe("jbd0050@moe.edu.my");
  });

  it("shows success message after sending", async () => {
    mockRequestMagicLink.mockResolvedValueOnce({
      message: "Magic link sent.",
      school_name: "SJK(T) Ladang Bikam",
    });

    render(<ClaimForm />);
    const input = screen.getByLabelText(/School email address/);
    fireEvent.change(input, { target: { value: "jbd0050@moe.edu.my" } });
    fireEvent.click(screen.getByRole("button", { name: /Send Verification Link/ }));

    await waitFor(() => {
      expect(screen.getByText(/Check your email/)).toBeInTheDocument();
    });
    expect(screen.getByText(/jbd0050@moe.edu.my/)).toBeInTheDocument();
    expect(screen.getByText(/SJK\(T\) Ladang Bikam/)).toBeInTheDocument();
  });

  it("shows error message on failure", async () => {
    mockRequestMagicLink.mockRejectedValueOnce(
      new Error("Only @moe.edu.my email addresses are accepted.")
    );

    render(<ClaimForm />);
    const input = screen.getByLabelText(/School email address/);
    fireEvent.change(input, { target: { value: "user@gmail.com" } });
    fireEvent.click(screen.getByRole("button", { name: /Send Verification Link/ }));

    await waitFor(() => {
      expect(screen.getByText(/moe.edu.my/)).toBeInTheDocument();
    });
  });

  it("disables button while loading", async () => {
    mockRequestMagicLink.mockImplementation(
      () => new Promise((resolve) => setTimeout(resolve, 1000))
    );

    render(<ClaimForm />);
    const input = screen.getByLabelText(/School email address/);
    fireEvent.change(input, { target: { value: "jbd0050@moe.edu.my" } });
    fireEvent.click(screen.getByRole("button", { name: /Send Verification Link/ }));

    await waitFor(() => {
      expect(screen.getByText("Sending...")).toBeInTheDocument();
    });
  });

  it("shows moe.edu.my hint text", () => {
    render(<ClaimForm />);
    expect(
      screen.getByText(/Only @moe.edu.my email addresses are accepted/)
    ).toBeInTheDocument();
  });
});
