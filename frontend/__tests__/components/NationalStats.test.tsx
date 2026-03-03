import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import NationalStats from "@/components/NationalStats";

describe("NationalStats", () => {
  const stats = {
    total_schools: 528,
    total_students: 85000,
    total_teachers: 8500,
    states: 12,
    constituencies_with_schools: 150,
    schools_under_30_students: 42,
  };

  it("renders all stat values", () => {
    render(<NationalStats stats={stats} />);
    expect(screen.getByText("528")).toBeInTheDocument();
    expect(screen.getByText("85,000")).toBeInTheDocument();
    expect(screen.getByText("8,500")).toBeInTheDocument();
    expect(screen.getByText("12")).toBeInTheDocument();
    expect(screen.getByText("42")).toBeInTheDocument();
  });

  it("renders stat labels", () => {
    render(<NationalStats stats={stats} />);
    expect(screen.getByText("Tamil Schools")).toBeInTheDocument();
    expect(screen.getByText("Students")).toBeInTheDocument();
    expect(screen.getByText("Teachers")).toBeInTheDocument();
    expect(screen.getByText("States")).toBeInTheDocument();
    expect(screen.getByText("Schools Under 30 Students")).toBeInTheDocument();
  });
});
