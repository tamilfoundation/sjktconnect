import "@testing-library/jest-dom";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import ImageManager from "@/components/ImageManager";
import { pinSchoolImage } from "@/lib/api";

jest.mock("@/lib/api", () => ({
  fetchSchoolImages: jest.fn().mockResolvedValue([]),
  reorderSchoolImages: jest.fn(),
  deleteSchoolImage: jest.fn(),
  pinSchoolImage: jest.fn().mockResolvedValue(undefined),
  updateImageCaption: jest.fn().mockResolvedValue({ id: 1, caption: "" }),
}));

import * as api from "@/lib/api";
const fetchSchoolImagesMock = api.fetchSchoolImages as jest.Mock;
const pinSchoolImageMock = pinSchoolImage as jest.Mock;
const updateImageCaptionMock = api.updateImageCaption as jest.Mock;

// All mocked images need the new caption field to satisfy SchoolImageData typing.
const baseImage = (overrides: Record<string, unknown>) => ({
  id: 1,
  image_url: "https://example.com/1.jpg",
  source: "PLACES",
  position: 0,
  is_primary: false,
  attribution: "",
  caption: "",
  ...overrides,
});

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
      baseImage({ id: 1, is_primary: true }),
      baseImage({ id: 2, image_url: "https://example.com/2.jpg", position: 1 }),
    ]);
    render(<ImageManager moeCode="ABC1234" />);
    await waitFor(() => expect(screen.getAllByRole("img")).toHaveLength(2));

    const heroButton = screen.getByRole("button", { name: /★ Hero/ });
    expect(heroButton).toBeDisabled();

    const makeHeroButton = screen.getByRole("button", { name: /Make hero/ });
    expect(makeHeroButton).not.toBeDisabled();
  });

  it("calls pinSchoolImage when Make hero is clicked", async () => {
    fetchSchoolImagesMock.mockResolvedValue([
      baseImage({ id: 1, is_primary: true }),
      baseImage({ id: 2, image_url: "https://example.com/2.jpg", position: 1 }),
    ]);
    render(<ImageManager moeCode="ABC1234" />);
    await waitFor(() => expect(screen.getAllByRole("img")).toHaveLength(2));

    fireEvent.click(screen.getByRole("button", { name: /Make hero/ }));
    await waitFor(() =>
      expect(pinSchoolImageMock).toHaveBeenCalledWith("ABC1234", 2),
    );

    await waitFor(() => {
      expect(screen.getByText("Hero photo updated.")).toBeInTheDocument();
    });
  });

  it("edits caption inline and persists via updateImageCaption", async () => {
    fetchSchoolImagesMock.mockResolvedValue([
      baseImage({ id: 7, caption: "" }),
    ]);
    updateImageCaptionMock.mockResolvedValueOnce({ id: 7, caption: "Hari Sukan" });

    render(<ImageManager moeCode="ABC1234" />);
    await waitFor(() => expect(screen.getByText("+ Add caption")).toBeInTheDocument());

    fireEvent.click(screen.getByText("+ Add caption"));
    const textarea = screen.getByPlaceholderText(/Add a short caption/);
    fireEvent.change(textarea, { target: { value: "Hari Sukan" } });
    fireEvent.click(screen.getByRole("button", { name: /Save/ }));

    await waitFor(() =>
      expect(updateImageCaptionMock).toHaveBeenCalledWith("ABC1234", 7, "Hari Sukan"),
    );
    await waitFor(() =>
      expect(screen.getByText("Caption saved.")).toBeInTheDocument(),
    );
    // Caption now displayed in the row instead of the placeholder
    expect(screen.getByText("Hari Sukan")).toBeInTheDocument();
    expect(screen.queryByText("+ Add caption")).not.toBeInTheDocument();
  });
});
