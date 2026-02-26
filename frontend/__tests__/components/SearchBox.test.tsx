import "@testing-library/jest-dom";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import SearchBox from "@/components/SearchBox";

// Mock the API module
jest.mock("@/lib/api", () => ({
  searchEntities: jest.fn(),
}));

import { searchEntities } from "@/lib/api";
const mockSearch = searchEntities as jest.MockedFunction<typeof searchEntities>;

describe("SearchBox", () => {
  const onSelect = jest.fn();
  const onClear = jest.fn();

  beforeEach(() => {
    jest.useFakeTimers();
    onSelect.mockClear();
    onClear.mockClear();
    mockSearch.mockClear();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it("renders search input", () => {
    render(<SearchBox onSelect={onSelect} onClear={onClear} />);
    expect(
      screen.getByPlaceholderText("Search schools or constituencies...")
    ).toBeInTheDocument();
  });

  it("does not search for single character", async () => {
    render(<SearchBox onSelect={onSelect} onClear={onClear} />);
    const input = screen.getByPlaceholderText(
      "Search schools or constituencies..."
    );

    fireEvent.change(input, { target: { value: "a" } });
    act(() => { jest.advanceTimersByTime(400); });

    expect(mockSearch).not.toHaveBeenCalled();
  });

  it("searches after debounce delay", async () => {
    mockSearch.mockResolvedValue({
      schools: [
        {
          moe_code: "JBD0050",
          name: "SJK(T) Ladang Bikam",
          short_name: "SJK(T) Ladang Bikam",
          state: "Johor",
          ppd: "PPD",
          constituency_code: "P140",
          constituency_name: "Segamat",
          enrolment: 120,
          teacher_count: 8,
          gps_lat: 2.5,
          gps_lng: 102.8,
          is_active: true,
        },
      ],
      constituencies: [],
    });

    render(<SearchBox onSelect={onSelect} onClear={onClear} />);
    const input = screen.getByPlaceholderText(
      "Search schools or constituencies..."
    );

    fireEvent.change(input, { target: { value: "bikam" } });
    await act(async () => { jest.advanceTimersByTime(400); });

    await waitFor(() => {
      expect(mockSearch).toHaveBeenCalledWith("bikam");
    });
  });

  it("shows clear button when query has text", () => {
    render(<SearchBox onSelect={onSelect} onClear={onClear} />);
    const input = screen.getByPlaceholderText(
      "Search schools or constituencies..."
    );

    // No clear button initially
    expect(screen.queryByLabelText("Clear search")).not.toBeInTheDocument();

    fireEvent.change(input, { target: { value: "test" } });
    expect(screen.getByLabelText("Clear search")).toBeInTheDocument();
  });

  it("calls onClear when clear button is clicked", () => {
    render(<SearchBox onSelect={onSelect} onClear={onClear} />);
    const input = screen.getByPlaceholderText(
      "Search schools or constituencies..."
    );

    fireEvent.change(input, { target: { value: "test" } });
    fireEvent.click(screen.getByLabelText("Clear search"));
    expect(onClear).toHaveBeenCalled();
  });

  it("calls onClear when input is emptied", () => {
    render(<SearchBox onSelect={onSelect} onClear={onClear} />);
    const input = screen.getByPlaceholderText(
      "Search schools or constituencies..."
    );

    fireEvent.change(input, { target: { value: "test" } });
    fireEvent.change(input, { target: { value: "" } });
    expect(onClear).toHaveBeenCalled();
  });
});
