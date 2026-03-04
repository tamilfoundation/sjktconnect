import "@testing-library/jest-dom";
import { render, screen, fireEvent } from "@testing-library/react";
import SupportSchoolCard from "@/components/SupportSchoolCard";

// Mock clipboard API
Object.assign(navigator, {
  clipboard: { writeText: jest.fn().mockResolvedValue(undefined) },
});

describe("SupportSchoolCard", () => {
  const defaultProps = {
    bankName: "Maybank",
    bankAccountNumber: "1234567890",
    bankAccountName: "PIBG SJK(T) Test School",
    moeCode: "JBD0050",
  };

  it("renders bank details when provided", () => {
    render(<SupportSchoolCard {...defaultProps} />);

    expect(screen.getByText("Maybank")).toBeInTheDocument();
    expect(screen.getByText("1234567890")).toBeInTheDocument();
    expect(screen.getByText("PIBG SJK(T) Test School")).toBeInTheDocument();
  });

  it("renders the support school heading", () => {
    render(<SupportSchoolCard {...defaultProps} />);

    expect(screen.getByText("Support This School")).toBeInTheDocument();
  });

  it("shows copy button", () => {
    render(<SupportSchoolCard {...defaultProps} />);

    expect(screen.getByText("Copy")).toBeInTheDocument();
  });

  it("copies account number on click", () => {
    render(<SupportSchoolCard {...defaultProps} />);

    fireEvent.click(screen.getByText("Copy"));
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith("1234567890");
  });

  it("renders DuitNow QR image", () => {
    render(<SupportSchoolCard {...defaultProps} />);

    const img = screen.getByAltText("DuitNow QR Code");
    expect(img).toBeInTheDocument();
    expect(img).toHaveAttribute(
      "src",
      expect.stringContaining("/api/v1/schools/JBD0050/duitnow-qr/")
    );
  });

  it("returns null when no bank account number", () => {
    const { container } = render(
      <SupportSchoolCard
        bankName=""
        bankAccountNumber=""
        bankAccountName=""
        moeCode="JBD0050"
      />
    );

    expect(container.innerHTML).toBe("");
  });
});
