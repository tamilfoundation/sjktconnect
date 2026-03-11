import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import ImageManager from "@/components/ImageManager";

// Mock the API
jest.mock("@/lib/api", () => ({
  fetchSchoolImages: jest.fn().mockResolvedValue([]),
  reorderSchoolImages: jest.fn(),
  deleteSchoolImage: jest.fn(),
}));

describe("ImageManager", () => {
  it("renders empty state when no images", async () => {
    render(<ImageManager moeCode="ABC1234" />);
    const emptyMessage = await screen.findByText("No images for this school.");
    expect(emptyMessage).toBeInTheDocument();
  });
});
