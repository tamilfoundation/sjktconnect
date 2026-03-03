import "@testing-library/jest-dom";
import { render, screen, fireEvent } from "@testing-library/react";
import Header from "@/components/Header";

// Mock window.matchMedia for the responsive breakpoint listener
beforeAll(() => {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: jest.fn().mockImplementation((query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: jest.fn(),
      removeListener: jest.fn(),
      addEventListener: jest.fn(),
      removeEventListener: jest.fn(),
      dispatchEvent: jest.fn(),
    })),
  });
});

describe("Header", () => {
  it("renders the site title", () => {
    render(<Header />);
    expect(screen.getByText("SJK(T) Connect")).toBeInTheDocument();
  });

  it("renders skip-to-content link", () => {
    render(<Header />);
    const skipLink = screen.getByText("Skip to content");
    expect(skipLink).toBeInTheDocument();
    expect(skipLink).toHaveAttribute("href", "#main-content");
  });

  it("renders nav group triggers on desktop", () => {
    render(<Header />);
    expect(screen.getByText("Explore")).toBeInTheDocument();
    expect(screen.getByText("Intelligence")).toBeInTheDocument();
    expect(screen.getByText("Resources")).toBeInTheDocument();
  });

  it("opens dropdown when group trigger is clicked", () => {
    render(<Header />);
    const trigger = screen.getAllByText("Explore")[0];
    fireEvent.click(trigger);

    // Dropdown items should now be visible
    expect(screen.getByText("School Map")).toBeInTheDocument();
    expect(screen.getByText("Constituencies")).toBeInTheDocument();
  });

  it("closes dropdown when clicking a different group", () => {
    render(<Header />);
    const exploreTrigger = screen.getAllByText("Explore")[0];
    fireEvent.click(exploreTrigger);
    expect(screen.getByText("School Map")).toBeInTheDocument();

    const intelTrigger = screen.getAllByText("Intelligence")[0];
    fireEvent.click(intelTrigger);
    expect(screen.getByText("News & Reports")).toBeInTheDocument();
  });

  it("renders Subscribe and Donate CTA buttons", () => {
    render(<Header />);
    const subscribeButtons = screen.getAllByText("Subscribe");
    const donateButtons = screen.getAllByText("Donate");
    expect(subscribeButtons.length).toBeGreaterThan(0);
    expect(donateButtons.length).toBeGreaterThan(0);
  });

  it("toggles mobile menu", () => {
    render(<Header />);
    const menuButton = screen.getByLabelText("Toggle menu");

    fireEvent.click(menuButton);

    // Mobile accordion group labels should be visible
    const exploreButtons = screen.getAllByText("Explore");
    // Desktop trigger + mobile accordion trigger
    expect(exploreButtons.length).toBeGreaterThanOrEqual(2);
  });

  it("expands mobile accordion group", () => {
    render(<Header />);
    const menuButton = screen.getByLabelText("Toggle menu");
    fireEvent.click(menuButton);

    // Find the mobile accordion trigger (last "Explore" button)
    const exploreButtons = screen.getAllByText("Explore");
    const mobileExplore = exploreButtons[exploreButtons.length - 1];
    fireEvent.click(mobileExplore);

    // Mobile items should now appear
    const schoolMapLinks = screen.getAllByText("School Map");
    expect(schoolMapLinks.length).toBeGreaterThanOrEqual(1);
  });

  it("sets aria-expanded on group triggers", () => {
    render(<Header />);
    const trigger = screen.getAllByText("Explore")[0];
    expect(trigger).toHaveAttribute("aria-expanded", "false");

    fireEvent.click(trigger);
    expect(trigger).toHaveAttribute("aria-expanded", "true");
  });

  it("closes dropdown on Escape key", () => {
    render(<Header />);
    const trigger = screen.getAllByText("Explore")[0];
    fireEvent.click(trigger);
    expect(screen.getByText("School Map")).toBeInTheDocument();

    fireEvent.keyDown(document, { key: "Escape" });
    expect(trigger).toHaveAttribute("aria-expanded", "false");
  });
});
