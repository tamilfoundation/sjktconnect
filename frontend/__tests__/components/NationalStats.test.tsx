import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import NationalStats from "@/components/NationalStats";

describe("NationalStats", () => {
  const stats = {
    total_schools: 528,
    total_students: 85000,
    total_preschool: 3200,
    total_special_needs: 150,
    total_teachers: 8500,
    states: 12,
    constituencies_with_schools: 150,
    schools_under_30_students: 42,
  };

  it("renders the section heading", () => {
    render(<NationalStats stats={stats} />);
    expect(screen.getByText("National Key Metrics")).toBeInTheDocument();
  });

  it("renders exact stat values", () => {
    render(<NationalStats stats={stats} />);
    expect(screen.getByText("85,000")).toBeInTheDocument();
    expect(screen.getByText("3,200")).toBeInTheDocument();
    expect(screen.getByText("150")).toBeInTheDocument();
    expect(screen.getByText("8,500")).toBeInTheDocument();
    expect(screen.getByText("42")).toBeInTheDocument();
  });

  it("renders stat labels", () => {
    render(<NationalStats stats={stats} />);
    expect(screen.getByText("Students")).toBeInTheDocument();
    expect(screen.getByText("Preschoolers")).toBeInTheDocument();
    expect(screen.getByText("Special Needs")).toBeInTheDocument();
    expect(screen.getByText("Teachers")).toBeInTheDocument();
    expect(screen.getByText("Under-Enrolled Schools")).toBeInTheDocument();
  });

  it("renders coloured accent borders", () => {
    const { container } = render(<NationalStats stats={stats} />);
    const cards = container.querySelectorAll(".border-l-4");
    expect(cards.length).toBe(5);
  });
});
