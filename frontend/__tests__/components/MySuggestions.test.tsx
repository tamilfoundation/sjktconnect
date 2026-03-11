import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import MySuggestions from "@/components/MySuggestions";

// Mock the API
jest.mock("@/lib/api", () => ({
  fetchMySuggestions: jest.fn().mockResolvedValue([]),
}));

describe("MySuggestions", () => {
  it("renders empty state when no suggestions", async () => {
    render(<MySuggestions />);
    // Wait for loading to finish
    const emptyMessage = await screen.findByText(
      "You haven't made any suggestions yet."
    );
    expect(emptyMessage).toBeInTheDocument();
  });

  it("renders heading", async () => {
    render(<MySuggestions />);
    const heading = await screen.findByText("My Suggestions");
    expect(heading).toBeInTheDocument();
  });
});
