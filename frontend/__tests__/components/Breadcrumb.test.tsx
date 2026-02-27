import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import Breadcrumb from "@/components/Breadcrumb";

describe("Breadcrumb", () => {
  it("renders all items", () => {
    render(
      <Breadcrumb
        items={[
          { label: "Home", href: "/" },
          { label: "Johor" },
        ]}
      />
    );
    expect(screen.getByText("Home")).toBeInTheDocument();
    expect(screen.getByText("Johor")).toBeInTheDocument();
  });

  it("renders links for items with href", () => {
    render(
      <Breadcrumb
        items={[
          { label: "Home", href: "/" },
          { label: "Current" },
        ]}
      />
    );
    const homeLink = screen.getByText("Home");
    expect(homeLink.closest("a")).toHaveAttribute("href", "/");
  });

  it("renders plain text for items without href", () => {
    render(
      <Breadcrumb
        items={[
          { label: "Home", href: "/" },
          { label: "Current" },
        ]}
      />
    );
    const current = screen.getByText("Current");
    expect(current.closest("a")).toBeNull();
  });

  it("renders separator between items", () => {
    render(
      <Breadcrumb
        items={[
          { label: "Home", href: "/" },
          { label: "Page" },
        ]}
      />
    );
    expect(screen.getByText("/")).toBeInTheDocument();
  });

  it("has breadcrumb aria label", () => {
    render(<Breadcrumb items={[{ label: "Home" }]} />);
    expect(screen.getByLabelText("Breadcrumb")).toBeInTheDocument();
  });
});
