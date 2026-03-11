import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import { useSession } from "next-auth/react";
import SuggestButton from "@/components/SuggestButton";

const mockUseSession = useSession as jest.Mock;

describe("SuggestButton", () => {
  afterEach(() => {
    jest.clearAllMocks();
  });

  it("renders the suggest button when session exists", () => {
    mockUseSession.mockReturnValue({
      data: { user: { name: "Test User", email: "test@example.com" } },
      status: "authenticated",
    });

    render(<SuggestButton moeCode="JBD0050" />);
    expect(
      screen.getByRole("button", { name: /Suggest an edit/i })
    ).toBeInTheDocument();
  });

  it("does not render when no session", () => {
    mockUseSession.mockReturnValue({
      data: null,
      status: "unauthenticated",
    });

    const { container } = render(<SuggestButton moeCode="JBD0050" />);
    expect(container.firstChild).toBeNull();
  });

  it("does not render while loading", () => {
    mockUseSession.mockReturnValue({
      data: null,
      status: "loading",
    });

    const { container } = render(<SuggestButton moeCode="JBD0050" />);
    expect(container.firstChild).toBeNull();
  });
});
