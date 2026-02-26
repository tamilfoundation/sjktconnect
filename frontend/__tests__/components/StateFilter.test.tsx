import "@testing-library/jest-dom";
import { render, screen, fireEvent } from "@testing-library/react";
import StateFilter from "@/components/StateFilter";

describe("StateFilter", () => {
  const defaultProps = {
    states: ["Johor", "Perak", "Selangor"],
    selectedState: "",
    onChange: jest.fn(),
    schoolCount: 528,
    totalCount: 528,
  };

  it("renders all state options plus 'All States'", () => {
    render(<StateFilter {...defaultProps} />);
    const select = screen.getByLabelText("Filter by State");
    expect(select).toBeInTheDocument();

    const options = screen.getAllByRole("option");
    // "All States" + 3 states
    expect(options).toHaveLength(4);
  });

  it("shows school count", () => {
    render(<StateFilter {...defaultProps} schoolCount={45} />);
    expect(screen.getByText(/Showing 45 of 528 schools/)).toBeInTheDocument();
  });

  it("calls onChange when state is selected", () => {
    const onChange = jest.fn();
    render(<StateFilter {...defaultProps} onChange={onChange} />);

    const select = screen.getByLabelText("Filter by State");
    fireEvent.change(select, { target: { value: "Perak" } });
    expect(onChange).toHaveBeenCalledWith("Perak");
  });

  it("calls onChange with empty string for 'All States'", () => {
    const onChange = jest.fn();
    render(
      <StateFilter
        {...defaultProps}
        selectedState="Johor"
        onChange={onChange}
      />
    );

    const select = screen.getByLabelText("Filter by State");
    fireEvent.change(select, { target: { value: "" } });
    expect(onChange).toHaveBeenCalledWith("");
  });

  it("marks the selected state", () => {
    render(<StateFilter {...defaultProps} selectedState="Selangor" />);
    const select = screen.getByLabelText("Filter by State") as HTMLSelectElement;
    expect(select.value).toBe("Selangor");
  });
});
