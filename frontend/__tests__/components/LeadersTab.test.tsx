/**
 * Sprint 20 — LeadersTab inline CRUD.
 */
import "@testing-library/jest-dom";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import LeadersTab from "@/components/edit_tabs/LeadersTab";
import { SchoolLeaderAdminData } from "@/lib/types";

const mockCreate = jest.fn();
const mockUpdate = jest.fn();
const mockDelete = jest.fn();
const mockRevalidate = jest.fn().mockResolvedValue(undefined);
jest.mock("@/lib/api", () => ({
  createSchoolLeader: (...args: unknown[]) => mockCreate(...args),
  updateSchoolLeader: (...args: unknown[]) => mockUpdate(...args),
  deleteSchoolLeader: (...args: unknown[]) => mockDelete(...args),
  revalidateSchoolPage: (...args: unknown[]) => mockRevalidate(...args),
}));

const mockPush = jest.fn();
const mockRefresh = jest.fn();
jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush, refresh: mockRefresh }),
}));

const baseLeader: SchoolLeaderAdminData = {
  id: 7,
  role: "headmaster",
  role_display: "Headmaster",
  name: "Pn. Devi",
  phone: "07-1234567",
  email: "hm@example.com",
};

beforeEach(() => {
  mockCreate.mockReset();
  mockUpdate.mockReset();
  mockDelete.mockReset();
  mockRevalidate.mockClear();
  mockPush.mockReset();
  mockRefresh.mockReset();
});

describe("LeadersTab — inline CRUD (Sprint 20)", () => {
  it("renders 4 role slots: existing leader as editable, others as + Add buttons", () => {
    render(<LeadersTab moeCode="JBD0050" initialLeaders={[baseLeader]} />);
    // Headmaster row populated
    expect((screen.getByLabelText("Name") as HTMLInputElement).value).toBe("Pn. Devi");
    expect((screen.getByLabelText(/Phone/) as HTMLInputElement).value).toBe("07-1234567");
    expect((screen.getByLabelText(/Email/) as HTMLInputElement).value).toBe("hm@example.com");
    // Other 3 roles show + Add buttons
    expect(screen.getByRole("button", { name: /Board Chairman/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /PTA Chairman/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Alumni/ })).toBeInTheDocument();
  });

  it("Save button is disabled when there are no changes", () => {
    render(<LeadersTab moeCode="JBD0050" initialLeaders={[baseLeader]} />);
    expect(screen.getByRole("button", { name: /Save changes/i })).toBeDisabled();
  });

  it("editing an existing leader's name calls updateSchoolLeader on save", async () => {
    mockUpdate.mockResolvedValueOnce({ ...baseLeader, name: "New Name" });
    render(<LeadersTab moeCode="JBD0050" initialLeaders={[baseLeader]} />);
    fireEvent.change(screen.getByLabelText("Name"), { target: { value: "New Name" } });
    fireEvent.click(screen.getByRole("button", { name: /Save changes/i }));
    await waitFor(() => {
      expect(mockUpdate).toHaveBeenCalledWith("JBD0050", 7, {
        name: "New Name",
        phone: "07-1234567",
        email: "hm@example.com",
      });
    });
  });

  it("clicking + Add reveals an editor; entering a name + saving creates a new leader", async () => {
    mockCreate.mockResolvedValueOnce({
      id: 11,
      role: "board_chair",
      role_display: "Board Chairman",
      name: "Tuan Chair",
      phone: "",
      email: "",
    });
    render(<LeadersTab moeCode="JBD0050" initialLeaders={[]} />);
    fireEvent.click(screen.getByRole("button", { name: /Board Chairman/ }));
    // Now an editor row should appear with empty inputs
    const nameInputs = screen.getAllByLabelText("Name");
    expect(nameInputs).toHaveLength(1);
    fireEvent.change(nameInputs[0], { target: { value: "Tuan Chair" } });
    fireEvent.click(screen.getByRole("button", { name: /Save changes/i }));

    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalledWith("JBD0050", "board_chair", {
        name: "Tuan Chair",
        phone: "",
        email: "",
      });
    });
  });

  it("clicking + Add without typing a name leaves Save button disabled", () => {
    render(<LeadersTab moeCode="JBD0050" initialLeaders={[]} />);
    fireEvent.click(screen.getByRole("button", { name: /Board Chairman/ }));
    expect(screen.getByRole("button", { name: /Save changes/i })).toBeDisabled();
    expect(mockCreate).not.toHaveBeenCalled();
  });

  it("Remove on an existing leader (after confirm) issues delete on save", async () => {
    mockDelete.mockResolvedValueOnce(undefined);
    const confirmSpy = jest.spyOn(window, "confirm").mockReturnValue(true);
    render(<LeadersTab moeCode="JBD0050" initialLeaders={[baseLeader]} />);
    fireEvent.click(screen.getByRole("button", { name: /Remove/ }));
    fireEvent.click(screen.getByRole("button", { name: /Save changes/i }));
    await waitFor(() => {
      expect(mockDelete).toHaveBeenCalledWith("JBD0050", 7);
    });
    confirmSpy.mockRestore();
  });

  it("backend role_taken error surfaces the slot-taken message", async () => {
    mockCreate.mockRejectedValueOnce(new Error("This school already has an active board_chair"));
    render(<LeadersTab moeCode="JBD0050" initialLeaders={[]} />);
    fireEvent.click(screen.getByRole("button", { name: /Board Chairman/ }));
    fireEvent.change(screen.getByLabelText("Name"), { target: { value: "X" } });
    fireEvent.click(screen.getByRole("button", { name: /Save changes/i }));
    await waitFor(() => {
      expect(screen.getByText(/already has an active leader/i)).toBeInTheDocument();
    });
  });

  it("blanking the name on an existing leader treats it as a delete", async () => {
    mockDelete.mockResolvedValueOnce(undefined);
    render(<LeadersTab moeCode="JBD0050" initialLeaders={[baseLeader]} />);
    fireEvent.change(screen.getByLabelText("Name"), { target: { value: "" } });
    fireEvent.click(screen.getByRole("button", { name: /Save changes/i }));
    await waitFor(() => {
      expect(mockDelete).toHaveBeenCalledWith("JBD0050", 7);
    });
  });
});
