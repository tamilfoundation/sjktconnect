import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
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
    expect(img.className).toContain("object-cover");
  });
});
