import "@testing-library/jest-dom";
import { render, screen, fireEvent } from "@testing-library/react";
import Header from "@/components/Header";

// Mock next/link
jest.mock("next/link", () => {
  return function MockLink({
    children,
    href,
    ...props
  }: {
    children: React.ReactNode;
    href: string;
    [key: string]: unknown;
  }) {
    return (
      <a href={href} {...props}>
        {children}
      </a>
    );
  };
});

describe("Header", () => {
  it("renders the site title", () => {
    render(<Header />);
    expect(screen.getByText("SJK(T) Connect")).toBeInTheDocument();
  });

  it("renders navigation links", () => {
    render(<Header />);
    const links = screen.getAllByText("School Map");
    expect(links.length).toBeGreaterThan(0);
  });

  it("renders Parliament Watch link", () => {
    render(<Header />);
    const links = screen.getAllByText("Parliament Watch");
    expect(links.length).toBeGreaterThan(0);
  });

  it("toggles mobile menu", () => {
    render(<Header />);
    const menuButton = screen.getByLabelText("Toggle menu");

    // Menu items in mobile dropdown should not be visible initially
    // (they exist in desktop nav but mobile dropdown is hidden)
    fireEvent.click(menuButton);

    // After click, mobile menu items should appear
    const mobileLinks = screen.getAllByText("School Map");
    expect(mobileLinks.length).toBeGreaterThanOrEqual(2); // desktop + mobile
  });
});
