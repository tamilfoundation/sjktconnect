import "@testing-library/jest-dom";
import { render, screen, waitFor } from "@testing-library/react";
import { useSession } from "next-auth/react";
import SuggestButton from "@/components/SuggestButton";

const mockFetchMe = jest.fn();
jest.mock("@/lib/api", () => ({
  fetchMe: () => mockFetchMe(),
}));

const mockUseSession = useSession as jest.Mock;

const authedSession = {
  data: { user: { name: "Test User", email: "test@example.com" } },
  status: "authenticated" as const,
};

beforeEach(() => {
  mockFetchMe.mockClear();
  mockUseSession.mockReturnValue(authedSession);
});

describe("SuggestButton", () => {
  it("renders the suggest button for a regular USER", async () => {
    mockFetchMe.mockResolvedValueOnce({
      id: 1,
      role: "USER",
      admin_school: null,
      email: "user@example.com",
    });
    render(<SuggestButton moeCode="JBD0050" />);
    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /Suggest an edit/i })
      ).toBeInTheDocument();
    });
  });

  it("renders the suggest button for an admin of a DIFFERENT school", async () => {
    mockFetchMe.mockResolvedValueOnce({
      id: 1,
      role: "USER",
      admin_school: { moe_code: "JBD0099", name: "Other" },
      email: "jbd0099@moe.edu.my",
    });
    render(<SuggestButton moeCode="JBD0050" />);
    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /Suggest an edit/i })
      ).toBeInTheDocument();
    });
  });

  it("does not render for SUPERADMIN (uses Edit instead)", async () => {
    mockFetchMe.mockResolvedValueOnce({
      id: 1,
      role: "SUPERADMIN",
      admin_school: null,
      email: "admin@tamilfoundation.org",
    });
    const { container } = render(<SuggestButton moeCode="JBD0050" />);
    await waitFor(() => {
      expect(mockFetchMe).toHaveBeenCalled();
    });
    expect(container.firstChild).toBeNull();
  });

  it("does not render for the bound admin of THIS school (uses Edit instead)", async () => {
    mockFetchMe.mockResolvedValueOnce({
      id: 1,
      role: "USER",
      admin_school: { moe_code: "JBD0050", name: "SJK(T) Ladang Bikam" },
      email: "jbd0050@moe.edu.my",
    });
    const { container } = render(<SuggestButton moeCode="JBD0050" />);
    await waitFor(() => {
      expect(mockFetchMe).toHaveBeenCalled();
    });
    expect(container.firstChild).toBeNull();
  });

  it("does not render when no session", () => {
    mockUseSession.mockReturnValue({ data: null, status: "unauthenticated" });
    const { container } = render(<SuggestButton moeCode="JBD0050" />);
    expect(container.firstChild).toBeNull();
    expect(mockFetchMe).not.toHaveBeenCalled();
  });

  it("does not render while loading", () => {
    mockUseSession.mockReturnValue({ data: null, status: "loading" });
    const { container } = render(<SuggestButton moeCode="JBD0050" />);
    expect(container.firstChild).toBeNull();
    expect(mockFetchMe).not.toHaveBeenCalled();
  });
});
