import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import ModerationQueue from "@/components/ModerationQueue";

// Mock the API
jest.mock("@/lib/api", () => ({
  fetchPendingSuggestions: jest.fn().mockResolvedValue([]),
  approveSuggestion: jest.fn(),
  rejectSuggestion: jest.fn(),
}));

describe("ModerationQueue", () => {
  it("renders empty state when no pending suggestions", async () => {
    render(<ModerationQueue />);
    const emptyMessage = await screen.findByText("No pending suggestions.");
    expect(emptyMessage).toBeInTheDocument();
  });
});
