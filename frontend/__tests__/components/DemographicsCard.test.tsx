import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import DemographicsCard from "@/components/DemographicsCard";

describe("DemographicsCard", () => {
  it("returns null when no data", () => {
    const { container } = render(
      <DemographicsCard
        indianPopulation={null}
        indianPercentage={null}
      />
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders demographics heading", () => {
    render(
      <DemographicsCard indianPopulation={5000} indianPercentage={10.5} />
    );
    expect(screen.getByText("Demographics")).toBeInTheDocument();
  });

  it("renders Indian population", () => {
    render(
      <DemographicsCard indianPopulation={5000} indianPercentage={10.5} />
    );
    expect(screen.getByText("5,000")).toBeInTheDocument();
  });

  it("renders Indian percentage", () => {
    render(
      <DemographicsCard indianPopulation={5000} indianPercentage={10.5} />
    );
    expect(screen.getByText("10.5%")).toBeInTheDocument();
  });

  it("renders average income", () => {
    render(
      <DemographicsCard
        indianPopulation={5000}
        indianPercentage={10.5}
        avgIncome={3500}
      />
    );
    expect(screen.getByText("RM 3,500")).toBeInTheDocument();
  });

  it("renders poverty rate", () => {
    render(
      <DemographicsCard
        indianPopulation={5000}
        indianPercentage={10.5}
        povertyRate={2.1}
      />
    );
    expect(screen.getByText("2.1%")).toBeInTheDocument();
  });

  it("renders gini index", () => {
    render(
      <DemographicsCard
        indianPopulation={5000}
        indianPercentage={10.5}
        gini={0.35}
      />
    );
    expect(screen.getByText("0.350")).toBeInTheDocument();
  });
});
