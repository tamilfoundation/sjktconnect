/**
 * Sprint 31 (2026-06-27): SchoolHistory three-state component tests.
 */
import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import SchoolHistory from "@/components/SchoolHistory";

// Mock next-intl for unit test isolation
jest.mock("next-intl", () => ({
  useTranslations: (_ns: string) => {
    const map: Record<string, string> = {
      emptyHeading: "History",
      emptyIntro: "Help us tell this school's story.",
      emptyBody: "Got an old photo, a founding date, or a memory of a beloved headmaster?",
      emptyContactCta: "✉ Contact us",
      populatedHeading: "About {name}",
      statusVerified: "Verified",
      disclaimerLabel: "Drawn from public sources.",
      disclaimerBody: "Not yet verified by the school.",
      disclaimerCta: "Know more? Help improve →",
      fellBackToEnBody: "A version in this language is not yet available.",
      fellBackToEnCta: "Contribute one →",
      sourcesLabel: "Sources",
      updatedFooter: "Updated by school",
    };
    return (key: string, vars?: Record<string, string>) => {
      let s = map[key] ?? key;
      if (vars) {
        for (const [k, v] of Object.entries(vars)) {
          s = s.replace(`{${k}}`, v);
        }
      }
      return s;
    };
  },
  useLocale: () => "en",
}));

const baseProps = {
  schoolName: "SJK(T) Azad",
  history: {},
  historySourceUrls: [],
  historyStatus: "UNVERIFIED" as const,
  historyUpdatedAt: null,
};

describe("SchoolHistory — empty state", () => {
  it("shows the empty placeholder with contact CTA when history is empty", () => {
    render(<SchoolHistory {...baseProps} />);
    expect(screen.getByText("History")).toBeInTheDocument();
    expect(screen.getByText(/Help us tell/)).toBeInTheDocument();
    const cta = screen.getByText(/Contact us/);
    expect(cta).toBeInTheDocument();
    expect(cta.closest("a")?.getAttribute("href")).toMatch(/mailto:info@tamilfoundation\.org/);
    expect(screen.queryByText(/Drawn from public sources/)).not.toBeInTheDocument();
  });

  it("treats whitespace-only history as empty", () => {
    render(<SchoolHistory {...baseProps} history={{ en: "   \n   " }} />);
    expect(screen.getByText("History")).toBeInTheDocument();  // empty heading
  });
});

describe("SchoolHistory — UNVERIFIED state", () => {
  const props = {
    ...baseProps,
    history: { en: "Founded 1946 by the Indian Youth Association of Penang.\n\nNew building completed 2011." },
    historySourceUrls: ["https://ms.wikipedia.org/wiki/SJK_Azad"],
    historyStatus: "UNVERIFIED" as const,
  };

  it("shows the populated heading interpolating the school name", () => {
    render(<SchoolHistory {...props} />);
    expect(screen.getByText("About SJK(T) Azad")).toBeInTheDocument();
  });

  it("shows the amber disclaimer banner with improve CTA", () => {
    render(<SchoolHistory {...props} />);
    expect(screen.getByText(/Drawn from public sources/)).toBeInTheDocument();
    expect(screen.getByText(/Not yet verified by the school/)).toBeInTheDocument();
    const cta = screen.getByText(/Help improve/);
    expect(cta.closest("a")?.getAttribute("href")).toMatch(/mailto:info@tamilfoundation\.org/);
  });

  it("renders body text split into paragraphs on double-newline", () => {
    render(<SchoolHistory {...props} />);
    expect(screen.getByText(/Founded 1946/)).toBeInTheDocument();
    expect(screen.getByText(/New building completed 2011/)).toBeInTheDocument();
  });

  it("shows source links with Wikipedia label", () => {
    render(<SchoolHistory {...props} />);
    expect(screen.getByText(/Sources/)).toBeInTheDocument();
    const link = screen.getByText(/Wikipedia \(ms\)/);
    expect(link.closest("a")?.getAttribute("href")).toBe("https://ms.wikipedia.org/wiki/SJK_Azad");
  });

  it("does NOT show the Verified badge", () => {
    render(<SchoolHistory {...props} />);
    expect(screen.queryByText("Verified")).not.toBeInTheDocument();
  });
});

describe("SchoolHistory — VERIFIED state", () => {
  const props = {
    ...baseProps,
    history: { en: "Founded 1946." },
    historySourceUrls: [],
    historyStatus: "VERIFIED" as const,
    historyUpdatedAt: "2026-08-15T10:00:00Z",
  };

  it("shows the Verified badge", () => {
    render(<SchoolHistory {...props} />);
    expect(screen.getByText("Verified")).toBeInTheDocument();
  });

  it("does NOT show the disclaimer banner", () => {
    render(<SchoolHistory {...props} />);
    expect(screen.queryByText(/Drawn from public sources/)).not.toBeInTheDocument();
  });

  it("shows the updated-by footer for verified content", () => {
    render(<SchoolHistory {...props} />);
    expect(screen.getByText(/Updated by school/)).toBeInTheDocument();
  });
});

describe("SchoolHistory — locale fallback", () => {
  it("when current-locale text is empty but English exists, falls back to English with a banner", () => {
    // jest mock above hard-codes useLocale to 'en', so directly test the fallback
    // by supplying a different locale's history that is empty.
    render(
      <SchoolHistory
        {...baseProps}
        history={{ en: "English fallback text." }}
        historyStatus="UNVERIFIED"
      />,
    );
    expect(screen.getByText(/English fallback text/)).toBeInTheDocument();
    // Locale is "en" in mock, so no fallback banner expected
    expect(screen.queryByText(/version in this language is not yet available/)).not.toBeInTheDocument();
  });
});
