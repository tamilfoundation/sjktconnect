import "@testing-library/jest-dom";
import { render, screen, fireEvent } from "@testing-library/react";
import ConstituencyList from "@/components/ConstituencyList";
import { Constituency } from "@/lib/types";

const makeConstituency = (
  overrides: Partial<Constituency> = {}
): Constituency => ({
  code: "P140",
  name: "Segamat",
  state: "Johor",
  mp_name: "Test MP",
  mp_party: "BN",
  school_count: 5,
  ...overrides,
});

describe("ConstituencyList", () => {
  it("renders all constituencies", () => {
    const constituencies = [
      makeConstituency({ code: "P140", name: "Segamat" }),
      makeConstituency({ code: "P141", name: "Sekijang" }),
    ];
    render(
      <ConstituencyList constituencies={constituencies} states={["Johor"]} />
    );
    expect(screen.getByText("Segamat")).toBeInTheDocument();
    expect(screen.getByText("Sekijang")).toBeInTheDocument();
  });

  it("shows state filter dropdown", () => {
    render(
      <ConstituencyList
        constituencies={[makeConstituency()]}
        states={["Johor", "Perak"]}
      />
    );
    expect(screen.getByLabelText("Filter by state")).toBeInTheDocument();
    expect(screen.getByText("All States")).toBeInTheDocument();
  });

  it("filters by state when selected", () => {
    const constituencies = [
      makeConstituency({ code: "P140", name: "Segamat", state: "Johor" }),
      makeConstituency({ code: "P060", name: "Ipoh Barat", state: "Perak" }),
    ];
    render(
      <ConstituencyList
        constituencies={constituencies}
        states={["Johor", "Perak"]}
      />
    );

    fireEvent.change(screen.getByLabelText("Filter by state"), {
      target: { value: "Johor" },
    });

    expect(screen.getByText("Segamat")).toBeInTheDocument();
    expect(screen.queryByText("Ipoh Barat")).not.toBeInTheDocument();
  });

  it("shows constituency count and school total", () => {
    const constituencies = [
      makeConstituency({ school_count: 5 }),
      makeConstituency({ code: "P141", school_count: 3 }),
    ];
    render(
      <ConstituencyList constituencies={constituencies} states={["Johor"]} />
    );
    expect(
      screen.getByText(/Showing 2 constituencies/)
    ).toBeInTheDocument();
    expect(screen.getByText(/8 Tamil schools/)).toBeInTheDocument();
  });

  it("renders constituency as link", () => {
    render(
      <ConstituencyList
        constituencies={[makeConstituency()]}
        states={["Johor"]}
      />
    );
    const link = screen.getByText("Segamat").closest("a");
    expect(link).toHaveAttribute("href", "/constituency/P140");
  });

  it("renders MP name and party", () => {
    render(
      <ConstituencyList
        constituencies={[makeConstituency()]}
        states={["Johor"]}
      />
    );
    expect(screen.getByText("Test MP")).toBeInTheDocument();
    expect(screen.getByText("BN")).toBeInTheDocument();
  });
});
