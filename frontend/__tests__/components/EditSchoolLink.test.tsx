import "@testing-library/jest-dom";
import { render, screen, waitFor } from "@testing-library/react";
import { useSession } from "next-auth/react";
import EditSchoolLink from "@/components/EditSchoolLink";

const mockFetchMe = jest.fn();
jest.mock("@/lib/api", () => ({
  fetchMe: () => mockFetchMe(),
}));

const mockUseSession = useSession as jest.Mock;

const authedSession = {
  data: { user: { name: "Test", email: "test@example.com" } },
  status: "authenticated" as const,
};

beforeEach(() => {
  mockFetchMe.mockClear();
  mockUseSession.mockReturnValue(authedSession);
});

describe("EditSchoolLink", () => {
  it("renders nothing when not authenticated", async () => {
    mockUseSession.mockReturnValue({ data: null, status: "unauthenticated" });
    const { container } = render(<EditSchoolLink moeCode="JBD0050" />);
    // Sprint 15 hotfix: when status !== "authenticated" we early-return without
    // calling fetchMe. The component should render nothing immediately.
    expect(container.firstChild).toBeNull();
    expect(mockFetchMe).not.toHaveBeenCalled();
  });

  it("renders nothing when admin of a different school", async () => {
    mockFetchMe.mockResolvedValueOnce({
      id: 1,
      role: "USER",
      admin_school: { moe_code: "JBD0099", name: "Other" },
      email: "jbd0099@moe.edu.my",
    });
    const { container } = render(<EditSchoolLink moeCode="JBD0050" />);
    await waitFor(() => {
      expect(mockFetchMe).toHaveBeenCalled();
    });
    expect(container.querySelector("a")).toBeNull();
  });

  it("renders edit link when admin for this school", async () => {
    mockFetchMe.mockResolvedValueOnce({
      id: 1,
      role: "USER",
      admin_school: { moe_code: "JBD0050", name: "SJK(T) Ladang Bikam" },
      email: "jbd0050@moe.edu.my",
    });
    render(<EditSchoolLink moeCode="JBD0050" />);
    await waitFor(() => {
      expect(screen.getByRole("link", { name: /Edit School Data/ })).toBeInTheDocument();
    });
    expect(screen.getByRole("link", { name: /Edit School Data/ })).toHaveAttribute(
      "href",
      "/school/JBD0050/edit"
    );
  });

  it("renders edit link for SUPERADMIN regardless of admin_school", async () => {
    mockFetchMe.mockResolvedValueOnce({
      id: 1,
      role: "SUPERADMIN",
      admin_school: null,
      email: "admin@tamilfoundation.org",
    });
    render(<EditSchoolLink moeCode="JBD0050" />);
    await waitFor(() => {
      expect(screen.getByRole("link", { name: /Edit School Data/ })).toBeInTheDocument();
    });
  });
});
