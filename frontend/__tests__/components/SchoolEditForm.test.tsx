import "@testing-library/jest-dom";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import SchoolEditForm from "@/components/SchoolEditForm";
import { SchoolEditData } from "@/lib/types";

const mockUpdateSchool = jest.fn();
const mockConfirmSchool = jest.fn();
jest.mock("@/lib/api", () => ({
  updateSchool: (...args: unknown[]) => mockUpdateSchool(...args),
  confirmSchool: (...args: unknown[]) => mockConfirmSchool(...args),
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
  email: "jbd0050@moe.edu.my",
  phone: "07-1234567",
  fax: "",
  gps_lat: 2.5,
  gps_lng: 102.8,
  enrolment: 120,
  preschool_enrolment: 15,
  special_enrolment: 0,
  teacher_count: 12,
  session_count: 1,
  session_type: "Pagi",
  last_verified: null,
  verified_by: "",
  bank_name: "",
  bank_account_name: "",
  bank_account_number: "",
};

beforeEach(() => {
  mockUpdateSchool.mockClear();
  mockConfirmSchool.mockClear();
});

describe("SchoolEditForm", () => {
  it("renders form fields with school data", () => {
    render(<SchoolEditForm school={mockSchool} />);
    expect(screen.getByLabelText(/Phone/)).toHaveValue("07-1234567");
    expect(screen.getByLabelText(/Student Enrolment/)).toHaveValue(120);
    expect(screen.getByLabelText(/Email/)).toHaveValue("jbd0050@moe.edu.my");
  });

  it("renders read-only fields as non-editable", () => {
    render(<SchoolEditForm school={mockSchool} />);
    const nameInput = screen.getByLabelText(/Official Name/);
    expect(nameInput).toHaveAttribute("readOnly");
  });

  it("renders confirm button", () => {
    render(<SchoolEditForm school={mockSchool} />);
    expect(
      screen.getByRole("button", { name: /Confirm Data/ })
    ).toBeInTheDocument();
  });

  it("renders save button", () => {
    render(<SchoolEditForm school={mockSchool} />);
    expect(
      screen.getByRole("button", { name: /Save Changes/ })
    ).toBeInTheDocument();
  });

  it("confirms data on button click", async () => {
    mockConfirmSchool.mockResolvedValueOnce({
      message: "School data confirmed.",
      last_verified: "2026-02-27T12:00:00Z",
      verified_by: "jbd0050@moe.edu.my",
    });

    render(<SchoolEditForm school={mockSchool} />);
    fireEvent.click(screen.getByRole("button", { name: /Confirm Data/ }));

    await waitFor(() => {
      expect(screen.getByText(/Data confirmed/)).toBeInTheDocument();
    });
    expect(mockConfirmSchool).toHaveBeenCalledWith("JBD0050");
  });

  it("saves changes on form submit", async () => {
    mockUpdateSchool.mockResolvedValueOnce({
      ...mockSchool,
      phone: "07-9999999",
      last_verified: "2026-02-27T12:00:00Z",
      verified_by: "jbd0050@moe.edu.my",
    });

    render(<SchoolEditForm school={mockSchool} />);
    const phoneInput = screen.getByLabelText(/Phone/);
    fireEvent.change(phoneInput, { target: { value: "07-9999999" } });
    fireEvent.click(screen.getByRole("button", { name: /Save Changes/ }));

    await waitFor(() => {
      expect(screen.getByText(/Changes saved/)).toBeInTheDocument();
    });
    expect(mockUpdateSchool).toHaveBeenCalledWith("JBD0050", {
      phone: "07-9999999",
    });
  });

  it("shows error when no changes to save", async () => {
    render(<SchoolEditForm school={mockSchool} />);
    fireEvent.click(screen.getByRole("button", { name: /Save Changes/ }));

    await waitFor(() => {
      expect(screen.getByText(/No changes to save/)).toBeInTheDocument();
    });
  });

  it("shows error on save failure", async () => {
    mockUpdateSchool.mockRejectedValueOnce(new Error("Server error"));

    render(<SchoolEditForm school={mockSchool} />);
    const phoneInput = screen.getByLabelText(/Phone/);
    fireEvent.change(phoneInput, { target: { value: "07-9999999" } });
    fireEvent.click(screen.getByRole("button", { name: /Save Changes/ }));

    await waitFor(() => {
      expect(screen.getByText(/Server error/)).toBeInTheDocument();
    });
  });

  it("shows last verified when present", () => {
    const verifiedSchool = {
      ...mockSchool,
      last_verified: "2026-02-27T10:00:00Z",
      verified_by: "jbd0050@moe.edu.my",
    };
    render(<SchoolEditForm school={verifiedSchool} />);
    expect(screen.getByText(/Last verified/)).toBeInTheDocument();
  });

  it("renders cancel link to school page", () => {
    render(<SchoolEditForm school={mockSchool} />);
    const cancelLink = screen.getByRole("link", { name: /Cancel/ });
    expect(cancelLink).toHaveAttribute("href", "/school/JBD0050");
  });
});
