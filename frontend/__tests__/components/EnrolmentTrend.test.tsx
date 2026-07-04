import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import EnrolmentTrend from "@/components/EnrolmentTrend";

const messages = {
  enrolmentTrend: {
    title: "Enrolment trend",
    source: "Source: MOE, {from} - {to}",
    since: "since {year}",
  },
};

function wrap(ui: React.ReactNode) {
  return (
    <NextIntlClientProvider messages={messages as any} locale="en">
      {ui}
    </NextIntlClientProvider>
  );
}

describe("EnrolmentTrend", () => {
  it("returns null when fewer than 2 data points", () => {
    const { container } = render(
      wrap(<EnrolmentTrend history={[{ date: "2018-01-01", students: 500 }]} />)
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders emerald line for an improving trend (+ glyph)", () => {
    render(
      wrap(
        <EnrolmentTrend
          history={[
            { date: "2018-01-01", students: 400 },
            { date: "2026-04-01", students: 500 },
          ]}
        />
      )
    );
    // Delta text carries a ▲ glyph + "+25%"
    expect(screen.getByText(/▲/)).toBeInTheDocument();
    expect(screen.getByText(/\+25%/)).toBeInTheDocument();
  });

  it("renders rose line for a declining trend (▼ glyph)", () => {
    render(
      wrap(
        <EnrolmentTrend
          history={[
            { date: "2018-01-01", students: 500 },
            { date: "2026-04-01", students: 400 },
          ]}
        />
      )
    );
    expect(screen.getByText(/▼/)).toBeInTheDocument();
    // -20% delta
    expect(screen.getByText(/-20%/)).toBeInTheDocument();
  });

  it("shows endpoint value labels", () => {
    // Use values that won't collide with the auto-generated Y-axis
    // gridlines (which land on rounded 50-multiples for this range).
    render(
      wrap(
        <EnrolmentTrend
          history={[
            { date: "2018-01-01", students: 517 },
            { date: "2022-06-01", students: 483 },
            { date: "2026-04-01", students: 427 },
          ]}
        />
      )
    );
    // Endpoints render as data-point value labels.
    expect(screen.getByText("517")).toBeInTheDocument();
    expect(screen.getByText("427")).toBeInTheDocument();
  });
});
