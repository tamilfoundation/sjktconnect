import "@testing-library/jest-dom";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import ModerationQueue from "@/components/ModerationQueue";

jest.mock("@/lib/api", () => ({
  fetchPendingSuggestions: jest.fn().mockResolvedValue([]),
  approveSuggestion: jest.fn().mockResolvedValue({}),
  rejectSuggestion: jest.fn().mockResolvedValue({}),
  approvePhotoSuggestion: jest.fn(),
}));

import * as api from "@/lib/api";
const fetchPendingMock = api.fetchPendingSuggestions as jest.Mock;
const approvePhotoMock = api.approvePhotoSuggestion as jest.Mock;

const photoSuggestion = {
  id: 42,
  school: "ABC1234",
  school_moe_code: "ABC1234",
  user_name: "Reg User",
  school_name: "SJK(T) Test",
  type: "PHOTO_UPLOAD" as const,
  status: "PENDING" as const,
  field_name: "",
  current_value: "",
  suggested_value: "",
  note: "",
  pending_image_url: "https://supabase.example/pending/abc.jpg",
  reviewed_by_name: null,
  review_note: "",
  points_awarded: 0,
  created_at: "2026-04-26T10:00:00Z",
};

describe("ModerationQueue", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("renders empty state when no pending suggestions", async () => {
    fetchPendingMock.mockResolvedValueOnce([]);
    render(<ModerationQueue />);
    expect(await screen.findByText("No pending suggestions.")).toBeInTheDocument();
  });

  it("renders pending photo with preview and school link", async () => {
    fetchPendingMock.mockResolvedValueOnce([photoSuggestion]);
    render(<ModerationQueue />);

    const img = await screen.findByAltText("Pending photo");
    expect(img).toHaveAttribute(
      "src",
      "https://supabase.example/pending/abc.jpg",
    );
    const schoolLink = screen.getByRole("link", { name: "SJK(T) Test" });
    expect(schoolLink).toHaveAttribute("href", expect.stringContaining("/school/ABC1234"));
  });

  it("shows slot-full banner when approve returns slot_full", async () => {
    fetchPendingMock.mockResolvedValueOnce([photoSuggestion]);
    approvePhotoMock.mockResolvedValueOnce({
      ok: false,
      slot_full: true,
      detail: "Photo slot full (20/20). Delete an existing photo first.",
    });
    render(<ModerationQueue />);
    await screen.findByAltText("Pending photo");

    fireEvent.click(screen.getByRole("button", { name: "Approve" }));

    await waitFor(() => {
      expect(
        screen.getByText(/20-photo limit/i),
      ).toBeInTheDocument();
    });
    // The suggestion should still be in the queue
    expect(screen.getByAltText("Pending photo")).toBeInTheDocument();
  });
});
