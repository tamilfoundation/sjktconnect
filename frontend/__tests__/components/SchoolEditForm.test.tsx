import "@testing-library/jest-dom";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import SchoolEditForm from "@/components/SchoolEditForm";
import { SchoolEditData } from "@/lib/types";

const mockUpdateSchool = jest.fn();
const mockRevalidate = jest.fn().mockResolvedValue(undefined);
jest.mock("@/lib/api", () => ({
  updateSchool: (...args: unknown[]) => mockUpdateSchool(...args),
  revalidateSchoolPage: (...args: unknown[]) => mockRevalidate(...args),
}));

const mockPush = jest.fn();
const mockRefresh = jest.fn();
jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush, refresh: mockRefresh }),
}));

const mockSchool: SchoolEditData = {
  moe_code: "JBD0050",
  name: "SJK(T) Ladang Bikam",
  short_name: "SJK(T) Ladang Bikam",
  name_tamil: "",
  address: "Ladang Bikam",
  postcode: "85000",
  city: "Segamat",
  state: "Johor",
  ppd: "Segamat",
  email: "jbd0050@moe.edu.my",
  phone: "07-1234567",
  fax: "",
  gps_lat: 2.5,
  gps_lng: 102.8,
  gps_verified: true,
  enrolment: 120,
  preschool_enrolment: 15,
  special_enrolment: 0,
  teacher_count: 12,
  grade: "B",
  assistance_type: "SBK",
  skm_eligible: false,
  location_type: "Bandar",
  session_count: 1,
  session_type: "Pagi",
  bank_name: "",
  bank_account_name: "",
  bank_account_number: "",
  claimed_at: null,
  leaders: [
    { id: 1, role: "headmaster", role_display: "Headmaster", name: "Pn. Test HM", phone: "", email: "" },
  ],
};

beforeEach(() => {
  mockUpdateSchool.mockClear();
  mockRevalidate.mockClear();
  mockPush.mockReset();
  mockRefresh.mockReset();
  // Reset window.location.hash so each test starts on the default tab.
  // (SchoolEditForm reads the hash on mount and persists it via
  // history.replaceState, which leaks between tests in the same jsdom
  // instance.)
  if (typeof window !== "undefined") {
    window.history.replaceState(null, "", window.location.pathname);
  }
});

describe("SchoolEditForm — tabs (Sprint 19)", () => {
  it("renders the 5-tab navigation", () => {
    render(<SchoolEditForm school={mockSchool} isSuperAdmin={false} />);
    expect(screen.getByRole("tab", { name: "Core" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Contact" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Leaders" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Support" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Images" })).toBeInTheDocument();
  });

  it("Core tab is active by default and shows enrolment field", () => {
    render(<SchoolEditForm school={mockSchool} isSuperAdmin={false} />);
    expect(screen.getByRole("tab", { name: "Core" })).toHaveAttribute(
      "aria-selected",
      "true"
    );
    expect(screen.getByLabelText(/Student Enrolment/)).toHaveValue(120);
  });

  it("does NOT render a Confirm Data button anywhere", () => {
    render(<SchoolEditForm school={mockSchool} isSuperAdmin={false} />);
    expect(screen.queryByRole("button", { name: /Confirm Data/ })).not.toBeInTheDocument();
    expect(screen.queryByText(/Is this information correct/)).not.toBeInTheDocument();
  });

  it("clicking the Contact tab swaps content", () => {
    render(<SchoolEditForm school={mockSchool} isSuperAdmin={false} />);
    fireEvent.click(screen.getByRole("tab", { name: "Contact" }));
    expect(screen.getByLabelText(/Address/)).toHaveValue("Ladang Bikam");
    expect(screen.getByLabelText(/Postcode/)).toHaveValue("85000");
  });

  it("Leaders tab shows existing leader as an editable row + a Save button", () => {
    // Sprint 20 replaced the read-only listing with inline CRUD.
    render(<SchoolEditForm school={mockSchool} isSuperAdmin={false} />);
    fireEvent.click(screen.getByRole("tab", { name: "Leaders" }));
    // Existing leader's name appears in the editable input
    const nameInput = screen.getByLabelText("Name") as HTMLInputElement;
    expect(nameInput.value).toBe("Pn. Test HM");
    // Save button now lives inside the LeadersTab itself
    expect(screen.getByRole("button", { name: /Save changes/i })).toBeInTheDocument();
    // The "coming soon" notice is gone
    expect(screen.queryByText(/coming soon/i)).not.toBeInTheDocument();
  });

  it("Leaders tab renders an + Add button for empty roles", () => {
    render(<SchoolEditForm school={mockSchool} isSuperAdmin={false} />);
    fireEvent.click(screen.getByRole("tab", { name: "Leaders" }));
    // mockSchool only has headmaster — board_chair, pta_chair, alumni_chair are empty
    expect(screen.getByRole("button", { name: /Board Chairman/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /PTA Chairman/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Alumni/ })).toBeInTheDocument();
  });

  it("Images tab links to the image manager", () => {
    render(<SchoolEditForm school={mockSchool} isSuperAdmin={false} />);
    fireEvent.click(screen.getByRole("tab", { name: "Images" }));
    const link = screen.getByRole("link", { name: /image manager/i });
    expect(link).toHaveAttribute("href", "/dashboard/images?school=JBD0050");
  });

  it("Contact tab GPS is read-only for non-SUPERADMIN", () => {
    render(<SchoolEditForm school={mockSchool} isSuperAdmin={false} />);
    fireEvent.click(screen.getByRole("tab", { name: "Contact" }));
    // The GPS section header carries the admin-only notice
    expect(screen.getByText(/SUPERADMIN/)).toBeInTheDocument();
  });

  it("Contact tab GPS is editable for SUPERADMIN", () => {
    render(<SchoolEditForm school={mockSchool} isSuperAdmin />);
    fireEvent.click(screen.getByRole("tab", { name: "Contact" }));
    expect(screen.getByLabelText(/Latitude/)).toHaveValue(2.5);
  });

  it("saves only changed fields on form submit", async () => {
    mockUpdateSchool.mockResolvedValueOnce({
      ...mockSchool,
      phone: "07-9999999",
    });

    render(<SchoolEditForm school={mockSchool} isSuperAdmin={false} />);
    fireEvent.click(screen.getByRole("tab", { name: "Contact" }));
    fireEvent.change(screen.getByLabelText(/Phone/), {
      target: { value: "07-9999999" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Save Changes/ }));

    await waitFor(() => {
      expect(screen.getByText(/Changes saved/)).toBeInTheDocument();
    });
    expect(mockUpdateSchool).toHaveBeenCalledWith("JBD0050", {
      phone: "07-9999999",
    });
  });

  it("shows error when no changes to save", async () => {
    render(<SchoolEditForm school={mockSchool} isSuperAdmin={false} />);
    fireEvent.click(screen.getByRole("button", { name: /Save Changes/ }));
    await waitFor(() => {
      expect(screen.getByText(/No changes to save/)).toBeInTheDocument();
    });
  });

  it("non-SUPERADMIN GPS edits are filtered out of the save payload", async () => {
    // Even if the formData has a different gps_lat (it can't via the UI for
    // non-admins, but defensively), the save should NOT send it.
    mockUpdateSchool.mockResolvedValueOnce({ ...mockSchool, name_tamil: "புதிய" });

    render(<SchoolEditForm school={mockSchool} isSuperAdmin={false} />);
    // Edit a normal field
    fireEvent.change(screen.getByLabelText(/Name \(Tamil\)/), {
      target: { value: "புதிய" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Save Changes/ }));

    await waitFor(() => {
      expect(mockUpdateSchool).toHaveBeenCalled();
    });
    const payload = mockUpdateSchool.mock.calls[0][1];
    expect(payload).not.toHaveProperty("gps_lat");
    expect(payload).not.toHaveProperty("gps_lng");
    expect(payload).toEqual({ name_tamil: "புதிய" });
  });
});
