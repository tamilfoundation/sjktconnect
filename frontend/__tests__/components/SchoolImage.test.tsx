import "@testing-library/jest-dom";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import SchoolImage from "@/components/SchoolImage";

// Bypass next/dynamic so the lightbox stub mounts synchronously in jsdom.
jest.mock("next/dynamic", () => (loader: () => Promise<{ default: React.ComponentType<unknown> }>) => {
  let Resolved: React.ComponentType<unknown> | null = null;
  loader().then((mod) => {
    Resolved = mod.default;
  });
  // eslint-disable-next-line react/display-name
  return (props: Record<string, unknown>) => {
    if (!Resolved) return null;
    const C = Resolved;
    return <C {...props} />;
  };
});

// Stub the lightbox so the dynamic import resolves synchronously in jsdom
// and we can assert on opens via a sentinel element.
jest.mock("@/components/PhotoLightbox", () => ({
  __esModule: true,
  default: (props: { open: boolean; index: number }) =>
    props.open ? (
      <div data-testid="lightbox" data-index={props.index} />
    ) : null,
}));

const baseImage = (overrides: Record<string, unknown>) => ({
  id: 1,
  image_url: "https://example.com/1.jpg",
  source: "PLACES" as const,
  position: 0,
  is_primary: false,
  attribution: "",
  caption: "",
  ...overrides,
});

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

  it("shows no-photo message when no images provided", () => {
    render(<SchoolImage schoolName="Test School" />);
    expect(screen.getByText(/no photo available/i)).toBeInTheDocument();
  });

  it("renders thumbnails for multiple images", () => {
    const images = [
      baseImage({ id: 1, is_primary: true }),
      baseImage({ id: 2, image_url: "https://example.com/2.jpg", position: 1 }),
      baseImage({ id: 3, image_url: "https://example.com/3.jpg", source: "SATELLITE", position: 2 }),
    ];
    render(<SchoolImage images={images} schoolName="Test School" />);
    const imgs = screen.getAllByRole("img");
    expect(imgs).toHaveLength(4); // 1 hero + 3 thumbs
    expect(imgs[0]).toHaveAttribute("src", "https://example.com/1.jpg");
  });

  it("swaps hero image when thumbnail is clicked", () => {
    const images = [
      baseImage({ id: 1, is_primary: true }),
      baseImage({ id: 2, image_url: "https://example.com/2.jpg", position: 1 }),
    ];
    render(<SchoolImage images={images} schoolName="Test School" />);

    const allImgs = screen.getAllByRole("img");
    expect(allImgs[0]).toHaveAttribute("src", "https://example.com/1.jpg");

    fireEvent.click(allImgs[2]);

    const updatedImgs = screen.getAllByRole("img");
    expect(updatedImgs[0]).toHaveAttribute("src", "https://example.com/2.jpg");
  });

  it("opens the lightbox when the hero is clicked", async () => {
    const images = [
      baseImage({ id: 1, is_primary: true, caption: "Front gate" }),
      baseImage({ id: 2, image_url: "https://example.com/2.jpg", position: 1 }),
    ];
    render(<SchoolImage images={images} schoolName="Test School" />);
    expect(screen.queryByTestId("lightbox")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Open Test School photo viewer/i }));

    const lightbox = await screen.findByTestId("lightbox");
    expect(lightbox).toHaveAttribute("data-index", "0");
  });

  it("shows 'View all N' overlay when there are more than 5 photos", async () => {
    const images = Array.from({ length: 7 }, (_, i) =>
      baseImage({
        id: i + 1,
        image_url: `https://example.com/${i + 1}.jpg`,
        position: i,
        is_primary: i === 0,
      }),
    );
    render(<SchoolImage images={images} schoolName="Test School" />);
    const overlay = screen.getByRole("button", { name: /View all 7 photos/i });
    expect(overlay).toBeInTheDocument();

    fireEvent.click(overlay);
    const lightbox = await screen.findByTestId("lightbox");
    expect(lightbox).toHaveAttribute("data-index", "0");
  });
});
