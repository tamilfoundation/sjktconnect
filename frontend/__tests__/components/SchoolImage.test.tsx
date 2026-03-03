import "@testing-library/jest-dom";
import { render, screen, fireEvent } from "@testing-library/react";
import SchoolImage from "@/components/SchoolImage";

describe("SchoolImage", () => {
  it("renders image with correct src and alt", () => {
    render(
      <SchoolImage
        imageUrl="https://maps.example.com/satellite.jpg"
        schoolName="SJK(T) Ladang Bikam"
      />
    );
    const img = screen.getByRole("img");
    expect(img).toHaveAttribute("src", "https://maps.example.com/satellite.jpg");
    expect(img).toHaveAttribute("alt", "SJK(T) Ladang Bikam");
  });

  it("uses lazy loading", () => {
    render(
      <SchoolImage
        imageUrl="https://maps.example.com/satellite.jpg"
        schoolName="Test School"
      />
    );
    const img = screen.getByRole("img");
    expect(img).toHaveAttribute("loading", "lazy");
  });

  it("applies responsive styling classes", () => {
    render(
      <SchoolImage
        imageUrl="https://maps.example.com/satellite.jpg"
        schoolName="Test School"
      />
    );
    const img = screen.getByRole("img");
    expect(img.className).toContain("w-full");
    expect(img.className).toContain("h-full");
    expect(img.className).toContain("object-cover");
  });

  it("shows no-photo message when no images provided", () => {
    render(<SchoolImage schoolName="Test School" />);
    expect(screen.getByText(/no photo available/i)).toBeInTheDocument();
  });

  it("renders thumbnails for multiple images", () => {
    const images = [
      { image_url: "https://example.com/1.jpg", source: "PLACES" as const, is_primary: true, attribution: "" },
      { image_url: "https://example.com/2.jpg", source: "PLACES" as const, is_primary: false, attribution: "" },
      { image_url: "https://example.com/3.jpg", source: "SATELLITE" as const, is_primary: false, attribution: "" },
    ];
    render(<SchoolImage images={images} schoolName="Test School" />);
    const imgs = screen.getAllByRole("img");
    // 1 hero + 3 overlay thumbnails (all shown, active one highlighted)
    expect(imgs).toHaveLength(4);
    expect(imgs[0]).toHaveAttribute("src", "https://example.com/1.jpg");
  });

  it("swaps hero image when thumbnail is clicked", () => {
    const images = [
      { image_url: "https://example.com/1.jpg", source: "PLACES" as const, is_primary: true, attribution: "" },
      { image_url: "https://example.com/2.jpg", source: "PLACES" as const, is_primary: false, attribution: "" },
    ];
    render(<SchoolImage images={images} schoolName="Test School" />);

    // Initially image 1 is the hero
    const allImgs = screen.getAllByRole("img");
    expect(allImgs[0]).toHaveAttribute("src", "https://example.com/1.jpg");

    // Click the second thumbnail (image 2) — thumbnails start at index 1
    fireEvent.click(allImgs[2]);

    // Now image 2 should be the hero
    const updatedImgs = screen.getAllByRole("img");
    expect(updatedImgs[0]).toHaveAttribute("src", "https://example.com/2.jpg");
  });
});
