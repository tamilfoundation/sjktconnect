import "@testing-library/jest-dom";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import PreferencesForm from "@/components/PreferencesForm";

const mockFetchPreferences = jest.fn();
const mockUpdatePreferences = jest.fn();
jest.mock("@/lib/api", () => ({
  fetchPreferences: (...args: unknown[]) => mockFetchPreferences(...args),
  updatePreferences: (...args: unknown[]) => mockUpdatePreferences(...args),
}));

const mockPreferencesResponse = {
  email: "user@example.com",
  name: "Test User",
  organisation: "",
  is_active: true,
  subscribed_at: "2026-03-01T00:00:00Z",
  preferences: {
    PARLIAMENT_WATCH: true,
    NEWS_WATCH: true,
    MONTHLY_BLAST: false,
  },
};

beforeEach(() => {
  mockFetchPreferences.mockClear();
  mockUpdatePreferences.mockClear();
});

describe("PreferencesForm", () => {
  it("shows loading state initially", () => {
    mockFetchPreferences.mockImplementation(() => new Promise(() => {}));
    render(<PreferencesForm token="test-token" />);
    expect(screen.getByText(/Loading preferences/)).toBeInTheDocument();
  });

  it("loads and displays preferences", async () => {
    mockFetchPreferences.mockResolvedValueOnce(mockPreferencesResponse);

    render(<PreferencesForm token="test-token" />);

    await waitFor(() => {
      expect(screen.getByText(/user@example.com/)).toBeInTheDocument();
    });
    expect(screen.getByText("Parliament Watch")).toBeInTheDocument();
    expect(screen.getByText("News Watch")).toBeInTheDocument();
    expect(screen.getByText("Monthly Intelligence Blast")).toBeInTheDocument();
  });

  it("calls fetchPreferences with token", async () => {
    mockFetchPreferences.mockResolvedValueOnce(mockPreferencesResponse);

    render(<PreferencesForm token="my-token" />);

    await waitFor(() => {
      expect(mockFetchPreferences).toHaveBeenCalledWith("my-token");
    });
  });

  it("renders checkboxes matching preference state", async () => {
    mockFetchPreferences.mockResolvedValueOnce(mockPreferencesResponse);

    render(<PreferencesForm token="test-token" />);

    await waitFor(() => {
      expect(screen.getByText(/user@example.com/)).toBeInTheDocument();
    });

    const checkboxes = screen.getAllByRole("checkbox");
    expect(checkboxes[0]).toBeChecked(); // PARLIAMENT_WATCH: true
    expect(checkboxes[1]).toBeChecked(); // NEWS_WATCH: true
    expect(checkboxes[2]).not.toBeChecked(); // MONTHLY_BLAST: false
  });

  it("toggles checkbox on click", async () => {
    mockFetchPreferences.mockResolvedValueOnce(mockPreferencesResponse);

    render(<PreferencesForm token="test-token" />);

    await waitFor(() => {
      expect(screen.getByText(/user@example.com/)).toBeInTheDocument();
    });

    const checkboxes = screen.getAllByRole("checkbox");
    fireEvent.click(checkboxes[0]); // Toggle PARLIAMENT_WATCH off
    expect(checkboxes[0]).not.toBeChecked();
  });

  it("saves preferences on button click", async () => {
    mockFetchPreferences.mockResolvedValueOnce(mockPreferencesResponse);
    mockUpdatePreferences.mockResolvedValueOnce({
      ...mockPreferencesResponse,
      preferences: {
        PARLIAMENT_WATCH: false,
        NEWS_WATCH: true,
        MONTHLY_BLAST: false,
      },
    });

    render(<PreferencesForm token="test-token" />);

    await waitFor(() => {
      expect(screen.getByText(/user@example.com/)).toBeInTheDocument();
    });

    // Toggle Parliament Watch off
    const checkboxes = screen.getAllByRole("checkbox");
    fireEvent.click(checkboxes[0]);

    // Save
    fireEvent.click(screen.getByRole("button", { name: /Save Preferences/ }));

    await waitFor(() => {
      expect(screen.getByText(/Preferences saved successfully/)).toBeInTheDocument();
    });
    expect(mockUpdatePreferences).toHaveBeenCalledWith("test-token", {
      PARLIAMENT_WATCH: false,
      NEWS_WATCH: true,
      MONTHLY_BLAST: false,
    });
  });

  it("shows error when save fails", async () => {
    mockFetchPreferences.mockResolvedValueOnce(mockPreferencesResponse);
    mockUpdatePreferences.mockRejectedValueOnce(
      new Error("Something went wrong.")
    );

    render(<PreferencesForm token="test-token" />);

    await waitFor(() => {
      expect(screen.getByText(/user@example.com/)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /Save Preferences/ }));

    await waitFor(() => {
      expect(screen.getByText(/Something went wrong/)).toBeInTheDocument();
    });
  });

  it("shows error for invalid token on load", async () => {
    mockFetchPreferences.mockRejectedValueOnce(
      new Error("Invalid preferences link.")
    );

    render(<PreferencesForm token="bad-token" />);

    await waitFor(() => {
      expect(screen.getByText(/Unable to load preferences/)).toBeInTheDocument();
    });
  });

  it("shows unsubscribe link", async () => {
    mockFetchPreferences.mockResolvedValueOnce(mockPreferencesResponse);

    render(<PreferencesForm token="test-token" />);

    await waitFor(() => {
      expect(screen.getByText(/user@example.com/)).toBeInTheDocument();
    });

    const link = screen.getByRole("link", { name: /Unsubscribe from all/ });
    expect(link).toHaveAttribute("href", "/unsubscribe/test-token");
  });

  it("disables button while saving", async () => {
    mockFetchPreferences.mockResolvedValueOnce(mockPreferencesResponse);
    mockUpdatePreferences.mockImplementation(
      () => new Promise((resolve) => setTimeout(resolve, 1000))
    );

    render(<PreferencesForm token="test-token" />);

    await waitFor(() => {
      expect(screen.getByText(/user@example.com/)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /Save Preferences/ }));

    await waitFor(() => {
      expect(screen.getByText("Saving...")).toBeInTheDocument();
    });
  });
});
