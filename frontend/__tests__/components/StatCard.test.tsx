import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import StatCard from "@/components/StatCard";

describe("StatCard", () => {
  it("renders label and string value", () => {
    render(<StatCard label="Grade" value="A" />);
    expect(screen.getByText("Grade")).toBeInTheDocument();
    expect(screen.getByText("A")).toBeInTheDocument();
  });

  it("formats numeric values with locale string", () => {
    render(<StatCard label="Students" value={1234} />);
    expect(screen.getByText("1,234")).toBeInTheDocument();
  });

  it("renders icon when provided", () => {
    render(<StatCard label="Test" value="OK" icon="📚" />);
    expect(screen.getByText("📚")).toBeInTheDocument();
  });
});
