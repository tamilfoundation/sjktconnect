import "@testing-library/jest-dom";
import { render, screen, waitFor } from "@testing-library/react";
import EditSchoolLink from "@/components/EditSchoolLink";

const mockFetchMe = jest.fn();
jest.mock("@/lib/api", () => ({
  fetchMe: () => mockFetchMe(),
}));

beforeEach(() => {
  mockFetchMe.mockClear();
});

describe("EditSchoolLink", () => {
  it("renders nothing when not authenticated", async () => {
    mockFetchMe.mockResolvedValueOnce(null);
    const { container } = render(<EditSchoolLink moeCode="JBD0050" />);
    // Wait for useEffect
    await waitFor(() => {
      expect(mockFetchMe).toHaveBeenCalled();
    });
    expect(container.firstChild).toBeNull();
  });

  it("renders nothing when authenticated for different school", async () => {
    mockFetchMe.mockResolvedValueOnce({
      school_moe_code: "JBD0099",
      school_name: "SJK(T) Other",
      email: "jbd0099@moe.edu.my",
    });
    const { container } = render(<EditSchoolLink moeCode="JBD0050" />);
    await waitFor(() => {
      expect(mockFetchMe).toHaveBeenCalled();
    });
    expect(container.querySelector("a")).toBeNull();
  });

  it("renders edit link when authenticated for this school", async () => {
    mockFetchMe.mockResolvedValueOnce({
      school_moe_code: "JBD0050",
      school_name: "SJK(T) Ladang Bikam",
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
});
