import "@testing-library/jest-dom";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import ImageManager from "@/components/ImageManager";
import { pinSchoolImage } from "@/lib/api";

jest.mock("@/lib/api", () => ({
  fetchSchoolImages: jest.fn().mockResolvedValue([]),
  reorderSchoolImages: jest.fn(),
  deleteSchoolImage: jest.fn(),
  pinSchoolImage: jest.fn().mockResolvedValue(undefined),
}));

import * as api from "@/lib/api";
const fetchSchoolImagesMock = api.fetchSchoolImages as jest.Mock;
const pinSchoolImageMock = pinSchoolImage as jest.Mock;

describe("ImageManager", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    fetchSchoolImagesMock.mockResolvedValue([]);
  });

  it("renders empty state when no images", async () => {
    render(<ImageManager moeCode="ABC1234" />);
    const emptyMessage = await screen.findByText("No images for this school.");
    expect(emptyMessage).toBeInTheDocument();
  });

  it("renders Make hero button on non-primary images and disabled badge on primary", async () => {
    fetchSchoolImagesMock.mockResolvedValue([
      {
        id: 1,
        image_url: "https://example.com/1.jpg",
        source: "PLACES",
        position: 0,
        is_primary: true,
        attribution: "",
      },
      {
        id: 2,
        image_url: "https://example.com/2.jpg",
        source: "PLACES",
        position: 1,
        is_primary: false,
        attribution: "",
      },
    ]);
    render(<ImageManager moeCode="ABC1234" />);
    await waitFor(() => expect(screen.getAllByRole("img")).toHaveLength(2));

    // Image 1 is primary → button shows "★ Hero" and is disabled
    const heroButton = screen.getByRole("button", { name: /★ Hero/ });
    expect(heroButton).toBeDisabled();

    // Image 2 is not primary → button shows "Make hero" and is enabled
    const makeHeroButton = screen.getByRole("button", { name: /Make hero/ });
    expect(makeHeroButton).not.toBeDisabled();
  });

  it("calls pinSchoolImage when Make hero is clicked", async () => {
    fetchSchoolImagesMock.mockResolvedValue([
      {
        id: 1,
        image_url: "https://example.com/1.jpg",
        source: "PLACES",
        position: 0,
        is_primary: true,
        attribution: "",
      },
      {
        id: 2,
        image_url: "https://example.com/2.jpg",
        source: "PLACES",
        position: 1,
        is_primary: false,
        attribution: "",
      },
    ]);
    render(<ImageManager moeCode="ABC1234" />);
    await waitFor(() => expect(screen.getAllByRole("img")).toHaveLength(2));

    fireEvent.click(screen.getByRole("button", { name: /Make hero/ }));
    await waitFor(() =>
      expect(pinSchoolImageMock).toHaveBeenCalledWith("ABC1234", 2),
    );

    // After pinning, the previously-primary image's button should now read "Make hero"
    // and the just-pinned one should read "★ Hero".
    await waitFor(() => {
      expect(screen.getByText("Hero photo updated.")).toBeInTheDocument();
    });
  });
});
