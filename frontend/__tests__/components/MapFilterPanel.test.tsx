import "@testing-library/jest-dom";
import { render, screen, fireEvent } from "@testing-library/react";
import MapFilterPanel, { ColourMode, FilterToggles } from "@/components/MapFilterPanel";

const defaultToggles: FilterToggles = {
  governmentAided: true,
  government: true,
  urban: true,
  rural: true,
  preschool: true,
  specialNeeds: true,
  both: true,
  none: true,
};

const renderPanel = (overrides: {
  colourMode?: ColourMode;
  toggles?: FilterToggles;
  enrolmentThreshold?: number;
  onColourModeChange?: jest.Mock;
  onToggleChange?: jest.Mock;
  onEnrolmentThresholdChange?: jest.Mock;
  onReset?: jest.Mock;
} = {}) => {
  const props = {
    colourMode: overrides.colourMode ?? "assistance" as ColourMode,
    onColourModeChange: overrides.onColourModeChange ?? jest.fn(),
    toggles: overrides.toggles ?? defaultToggles,
    onToggleChange: overrides.onToggleChange ?? jest.fn(),
    enrolmentThreshold: overrides.enrolmentThreshold ?? 30,
    onEnrolmentThresholdChange: overrides.onEnrolmentThresholdChange ?? jest.fn(),
    onReset: overrides.onReset ?? jest.fn(),
    filteredCount: 500,
    totalCount: 528,
  };
  return render(<MapFilterPanel {...props} />);
};

describe("MapFilterPanel", () => {
  it("renders filter heading and reset button", () => {
    renderPanel();
    expect(screen.getByText("Filters")).toBeInTheDocument();
    expect(screen.getByText("Reset All")).toBeInTheDocument();
  });

  it("renders colour mode pills", () => {
    renderPanel();
    expect(screen.getByText("Assistance")).toBeInTheDocument();
    expect(screen.getByText("Location")).toBeInTheDocument();
    expect(screen.getByText("Programmes")).toBeInTheDocument();
    expect(screen.getByText("Enrolment")).toBeInTheDocument();
  });

  it("renders assistance toggles by default", () => {
    renderPanel({ colourMode: "assistance" });
    expect(screen.getByText("Government-Aided")).toBeInTheDocument();
    expect(screen.getByText("Government")).toBeInTheDocument();
  });

  it("renders location toggles when location mode selected", () => {
    renderPanel({ colourMode: "location" });
    expect(screen.getByText("Urban")).toBeInTheDocument();
    expect(screen.getByText("Rural")).toBeInTheDocument();
  });

  it("renders programmes toggles when programmes mode selected", () => {
    renderPanel({ colourMode: "programmes" });
    expect(screen.getByText("Preschool")).toBeInTheDocument();
    expect(screen.getByText("Special Needs")).toBeInTheDocument();
    expect(screen.getByText("Both")).toBeInTheDocument();
    expect(screen.getByText("None")).toBeInTheDocument();
  });

  it("renders enrolment slider when enrolment mode selected", () => {
    renderPanel({ colourMode: "enrolment", enrolmentThreshold: 25 });
    expect(screen.getByRole("slider")).toBeInTheDocument();
    expect(screen.getByText("≤ 25")).toBeInTheDocument();
  });

  it("calls onColourModeChange when pill clicked", () => {
    const onColourModeChange = jest.fn();
    renderPanel({ onColourModeChange });
    fireEvent.click(screen.getByText("Location"));
    expect(onColourModeChange).toHaveBeenCalledWith("location");
  });

  it("calls onReset when Reset All clicked", () => {
    const onReset = jest.fn();
    renderPanel({ onReset });
    fireEvent.click(screen.getByText("Reset All"));
    expect(onReset).toHaveBeenCalled();
  });

  it("displays school count", () => {
    renderPanel();
    expect(screen.getByText(/500 of 528/)).toBeInTheDocument();
  });

  it("displays context-sensitive info note", () => {
    renderPanel({ colourMode: "assistance" });
    expect(screen.getByText(/funding type/)).toBeInTheDocument();
  });
});
