import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import ElectoralInfluenceCard from "@/components/ElectoralInfluenceCard";
import { ElectoralInfluence } from "@/lib/types";
import messages from "@/messages/en.json";

function renderCard(
  influence: ElectoralInfluence | null,
  props?: { constituencyName?: string; constituencyCode?: string; state?: string }
) {
  return render(
    <NextIntlClientProvider locale="en" messages={messages}>
      <ElectoralInfluenceCard influence={influence} {...props} />
    </NextIntlClientProvider>
  );
}

describe("ElectoralInfluenceCard", () => {
  const kingmaker: ElectoralInfluence = {
    indian_voters: 12800,
    winning_margin: 348,
    ratio: 36.8,
    verdict: "kingmaker",
  };

  const significant: ElectoralInfluence = {
    indian_voters: 8000,
    winning_margin: 5000,
    ratio: 1.6,
    verdict: "significant",
  };

  const safeSeat: ElectoralInfluence = {
    indian_voters: 4000,
    winning_margin: 30000,
    ratio: 0.1,
    verdict: "safe_seat",
  };

  it("renders nothing when influence is null", () => {
    const { container } = renderCard(null);
    expect(container.firstChild).toBeNull();
  });

  it("renders power meter for kingmaker", () => {
    renderCard(kingmaker);
    expect(screen.getByText("Power Meter")).toBeInTheDocument();
  });

  it("shows indian voters count", () => {
    renderCard(kingmaker);
    expect(screen.getByText("12,800")).toBeInTheDocument();
  });

  it("shows winning margin", () => {
    renderCard(kingmaker);
    expect(screen.getByText("348")).toBeInTheDocument();
  });

  it("shows ratio", () => {
    renderCard(kingmaker);
    // Ratio is split: "36.8" + "x" in separate elements
    expect(screen.getByText("36.8", { exact: false })).toBeInTheDocument();
  });

  it("shows Kingmaker verdict for high ratio", () => {
    renderCard(kingmaker);
    expect(screen.getByText("Kingmaker")).toBeInTheDocument();
  });

  it("shows Significant verdict for medium ratio", () => {
    renderCard(significant);
    expect(screen.getByText("Significant")).toBeInTheDocument();
  });

  it("shows Safe Seat verdict for low ratio", () => {
    renderCard(safeSeat);
    expect(screen.getByText("Safe Seat")).toBeInTheDocument();
  });

  it("renders capsule power meter", () => {
    const { container } = renderCard(kingmaker);
    // Single capsule fill element with height style
    const fill = container.querySelectorAll("[style*='height']");
    expect(fill.length).toBe(1);
  });

  it("shows DOSM and Wikipedia links when props provided", () => {
    renderCard(kingmaker, {
      constituencyName: "Bagan Datuk",
      constituencyCode: "P075",
      state: "PERAK",
    });
    const dosmLink = screen.getByText("DOSM Kawasanku");
    expect(dosmLink).toBeInTheDocument();
    expect(dosmLink.closest("a")).toHaveAttribute("target", "_blank");

    const wikiLink = screen.getByText("Wikipedia");
    expect(wikiLink).toBeInTheDocument();
    expect(wikiLink.closest("a")).toHaveAttribute("target", "_blank");
  });

  it("hides links when no constituency props provided", () => {
    renderCard(kingmaker);
    expect(screen.queryByText("DOSM Kawasanku")).not.toBeInTheDocument();
    expect(screen.queryByText("Wikipedia")).not.toBeInTheDocument();
  });
});
